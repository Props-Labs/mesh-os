"""
CLI interface for MeshOS.
"""
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import subprocess
import time
import json
from uuid import UUID

import click
from dotenv import load_dotenv, find_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import print as rprint

from mesh_os.core.client import MeshOS, InvalidSlugError
from mesh_os.core.taxonomy import (
    DataType, EdgeType, MemoryMetadata, EdgeMetadata,
    ActivitySubtype, KnowledgeSubtype, DecisionSubtype, MediaSubtype
)

console = Console()

def validate_uuid(ctx, param, value: str) -> str:
    """Validate UUID format."""
    try:
        UUID(value)
        return value
    except ValueError:
        raise click.BadParameter(f"Invalid UUID format: {value}", param=param)

def validate_metadata(metadata_str: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse and validate metadata JSON."""
    if not metadata_str:
        return None
    try:
        metadata = json.loads(metadata_str)
        if not isinstance(metadata, dict):
            raise click.BadParameter("Metadata must be a JSON object")
        return metadata
    except json.JSONDecodeError:
        raise click.BadParameter("Invalid JSON format")

def validate_memory_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Validate memory metadata against our taxonomy."""
    if "type" not in metadata:
        raise click.BadParameter("Memory metadata must include 'type' field")
    if "subtype" not in metadata:
        raise click.BadParameter("Memory metadata must include 'subtype' field")
    
    try:
        data_type = DataType(metadata["type"])
        subtype_map = {
            DataType.ACTIVITY: ActivitySubtype,
            DataType.KNOWLEDGE: KnowledgeSubtype,
            DataType.DECISION: DecisionSubtype,
            DataType.MEDIA: MediaSubtype
        }
        subtype_enum = subtype_map[data_type]
        subtype = subtype_enum(metadata["subtype"])
        
        # Create MemoryMetadata to validate the full structure
        MemoryMetadata(**metadata)
        return metadata
    except ValueError as e:
        raise click.BadParameter(str(e))

def validate_edge_type(ctx, param, value: str) -> str:
    """Validate edge relationship type."""
    try:
        EdgeType(value)
        return value
    except ValueError:
        valid_types = [e.value for e in EdgeType]
        raise click.BadParameter(
            f"Invalid relationship type. Must be one of: {', '.join(valid_types)}"
        )

def validate_weight(ctx, param, value: float) -> float:
    """Validate edge weight."""
    if not 0.0 <= value <= 1.0:
        raise click.BadParameter("Weight must be between 0.0 and 1.0")
    return value

def load_env():
    """Load environment variables from .env file in current directory."""
    env_file = find_dotenv(usecwd=True)
    if env_file:
        load_dotenv(env_file)
        return True
    return False

def get_client():
    """Get a configured MeshOS client."""
    # Try to load environment from current directory
    load_env()
    
    hasura_url = os.getenv("HASURA_URL", "http://localhost:8080/v1/graphql")
    hasura_admin_secret = os.getenv("HASURA_ADMIN_SECRET", "meshos")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        if not setup_openai_key(Path(".env")):
            raise ValueError("OpenAI API key is required")
        # Reload environment after setting up the key
        load_env()
        openai_api_key = os.getenv("OPENAI_API_KEY")
    
    return MeshOS(
        url=hasura_url,
        api_key=hasura_admin_secret,
        openai_api_key=openai_api_key
    )

def setup_openai_key(env_file: Path) -> bool:
    """
    Guide user through OpenAI API key setup.
    Returns True if key was configured successfully.
    """
    console.print(Panel(
        "[yellow]⚠️  OpenAI API key required[/]\n\n"
        "MeshOS uses OpenAI's API for generating embeddings.\n"
        "You can get an API key at: [blue]https://platform.openai.com/api-keys[/]",
        title="API Key Setup",
        border_style="yellow"
    ))
    
    if click.confirm("Would you like to enter your OpenAI API key now?", default=True):
        api_key = Prompt.ask(
            "Enter your OpenAI API key",
            password=True,
            show_default=False
        )
        
        # Read existing .env content
        env_content = env_file.read_text() if env_file.exists() else ""
        
        # Replace or add OPENAI_API_KEY
        if "OPENAI_API_KEY=" in env_content:
            env_content = "\n".join(
                line if not line.startswith("OPENAI_API_KEY=") else f"OPENAI_API_KEY={api_key}"
                for line in env_content.splitlines()
            )
        else:
            env_content += f"\n# OpenAI Configuration\nOPENAI_API_KEY={api_key}\n"
        
        # Write updated content
        env_file.write_text(env_content)
        console.print("[green]✓[/] API key saved to .env file")
        
        # Set the environment variable for the current process
        os.environ["OPENAI_API_KEY"] = api_key
        return True
    
    console.print(
        "\n[yellow]Note:[/] You'll need to set OPENAI_API_KEY in your .env file before using MeshOS"
    )
    return False

# Get the package root directory
PACKAGE_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PACKAGE_ROOT / "templates"

@click.group()
def cli():
    """MeshOS CLI - Manage your agent memory system."""
    pass

@cli.group()
def agent():
    """Manage agents."""
    pass

@agent.command()
@click.argument("name")
@click.option("--description", "-d", help="Agent description")
@click.option("--metadata", "-m", help="Agent metadata as JSON")
@click.option("--slug", "-s", help="Unique slug for the agent (lowercase with hyphens/underscores)")
def register(name: str, description: Optional[str] = None, metadata: Optional[str] = None, slug: Optional[str] = None):
    """Register a new agent."""
    try:
        client = get_client()
        metadata_dict = validate_metadata(metadata)
        agent = client.register_agent(name, description, metadata_dict, slug)
        if agent.slug:
            console.print(f"[green]✓[/] Agent registered with ID: {agent.id} (slug: {agent.slug})")
        else:
            console.print(f"[green]✓[/] Agent registered with ID: {agent.id}")
    except InvalidSlugError as e:
        console.print(f"[red]Error:[/] Invalid slug format: {str(e)}")
        raise click.ClickException(str(e))
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")
        raise click.ClickException(str(e))

@agent.command()
@click.argument("agent_id")
def unregister(agent_id: str):
    """Unregister an agent by ID or slug."""
    try:
        client = get_client()
        # Try to get agent by slug first
        agent = None
        try:
            agent = client.get_agent_by_slug(agent_id)
        except InvalidSlugError:
            # Not a valid slug, try UUID
            try:
                agent_id = validate_uuid(None, None, agent_id)
            except click.BadParameter as e:
                console.print(f"[red]Error:[/] {str(e)}")
                raise click.ClickException("Agent ID must be a valid UUID or slug")
        
        if not agent:
            # If we got here, we have a valid UUID but need to check if agent exists
            agent = client.get_agent(agent_id)
            if not agent:
                console.print(f"[red]Error:[/] Agent {agent_id} not found")
                raise click.ClickException("Agent not found")
        
        # Now we have a valid agent, unregister it
        if client.unregister_agent(agent.id):
            identifier = agent.slug or agent.id
            console.print(f"[green]✓[/] Agent {identifier} unregistered")
        else:
            console.print(f"[red]Error:[/] Failed to unregister agent {agent_id}")
            raise click.ClickException("Failed to unregister agent")
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")
        raise click.ClickException(str(e))

@agent.command()
@click.argument("identifier")
@click.argument("status")
def update_status(identifier: str, status: str):
    """Update an agent's status by ID or slug.
    
    Valid statuses: active, inactive, error
    """
    try:
        client = get_client()
        # Try to get agent by slug first
        agent = None
        try:
            agent = client.get_agent_by_slug(identifier)
        except InvalidSlugError:
            # Not a valid slug, try UUID
            try:
                identifier = validate_uuid(None, None, identifier)
            except click.BadParameter as e:
                console.print(f"[red]Error:[/] {str(e)}")
                raise click.ClickException("Agent ID must be a valid UUID or slug")
        
        if not agent:
            # If we got here, we have a valid UUID but need to check if agent exists
            agent = client.get_agent(identifier)
            if not agent:
                console.print(f"[red]Error:[/] Agent {identifier} not found")
                raise click.ClickException("Agent not found")
        
        # Validate status
        valid_statuses = ["active", "inactive", "error"]
        if status.lower() not in valid_statuses:
            console.print(f"[red]Error:[/] Invalid status. Must be one of: {', '.join(valid_statuses)}")
            raise click.ClickException("Invalid status")
        
        # Update the agent's status
        updated_agent = client.update_agent_status(agent.id, status.lower())
        identifier = updated_agent.slug or updated_agent.id
        console.print(f"[green]✓[/] Agent {identifier} status updated to: {updated_agent.status}")
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")
        raise click.ClickException(str(e))

@cli.group()
def memory():
    """Manage memories."""
    pass

@memory.command()
@click.argument("content")
@click.option("--agent-id", "-a", callback=validate_uuid, help="Agent ID to associate with the memory")
@click.option("--metadata", "-m", help="Memory metadata as JSON")
def remember(content: str, agent_id: Optional[str] = None, metadata: Optional[str] = None):
    """Store a new memory."""
    try:
        client = get_client()
        metadata_dict = validate_metadata(metadata)
        if metadata_dict:
            metadata_dict = validate_memory_metadata(metadata_dict)
        memory = client.remember(content, agent_id, metadata_dict)
        console.print(f"[green]✓[/] Memory stored with ID: {memory.id}")
    except click.BadParameter as e:
        console.print(f"[red]Error:[/] {str(e)}")
        raise
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")
        raise click.ClickException(str(e))

@memory.command()
@click.argument("query")
@click.option("--agent-id", "-a", callback=validate_uuid, help="Filter memories by agent ID")
@click.option("--limit", "-l", default=5, type=click.IntRange(1, 100), help="Maximum number of results (1-100)")
@click.option("--threshold", "-t", default=0.7, callback=validate_weight, help="Similarity threshold (0-1)")
@click.option("--filter", "-f", multiple=True, help="Add metadata filters in format key=value or key.operator=value")
def recall(query: str, agent_id: Optional[str] = None, limit: int = 5, threshold: float = 0.7, filter: Tuple[str, ...] = ()):
    """Search for similar memories with optional filters."""
    try:
        client = get_client()
        filters = {}
        
        for f in filter:
            if "=" not in f:
                raise click.BadParameter(f"Invalid filter format: {f}")
            
            key, value = f.split("=", 1)
            
            if "._" in key:
                base_key, operator = key.split("._", 1)
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError:
                    parsed_value = value
                filters[base_key] = {f"_{operator}": parsed_value}
            else:
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError:
                    parsed_value = value
                filters[key] = parsed_value
        
        memories = client.recall(query, agent_id, limit, threshold, filters)
        if not memories:
            console.print("[yellow]No matching memories found[/]")
            return
        
        console.print(f"\n[green]Found {len(memories)} matching memories:[/]\n")
        for memory in memories:
            metadata_str = json.dumps(memory.metadata.model_dump(), indent=2)
            console.print(Panel(
                f"{memory.content}\n\n"
                f"[blue]Agent:[/] {memory.agent_id or 'None'}\n"
                f"[blue]Created:[/] {memory.created_at}\n"
                f"[blue]Updated:[/] {memory.updated_at}\n"
                f"[blue]Metadata:[/] {metadata_str}",
                title=f"Memory {memory.id}",
                border_style="blue"
            ))
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")

@memory.command()
@click.argument("memory_id", callback=validate_uuid)
def forget(memory_id: str):
    """Delete a memory."""
    try:
        client = get_client()
        if client.forget(memory_id):
            console.print(f"[green]✓[/] Memory {memory_id} deleted")
        else:
            console.print(f"[red]Error:[/] Memory {memory_id} not found")
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")

@memory.command()
@click.argument("source_id", callback=validate_uuid)
@click.argument("target_id", callback=validate_uuid)
@click.option("--relationship", "-r", required=True, callback=validate_edge_type, 
              help="Type of relationship (e.g., 'related_to', 'version_of')")
@click.option("--weight", "-w", default=1.0, callback=validate_weight, 
              help="Weight of the connection (0-1)")
def link(source_id: str, target_id: str, relationship: str, weight: float):
    """Create a link between two memories."""
    try:
        client = get_client()
        edge = client.link_memories(source_id, target_id, relationship, weight)
        console.print(f"[green]✓[/] Created {relationship} link with ID: {edge.id}")
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")

@memory.command()
@click.argument("source_id", callback=validate_uuid)
@click.argument("target_id", callback=validate_uuid)
@click.option("--relationship", "-r", help="Type of relationship to remove (if not specified, removes all relationships)")
def unlink(source_id: str, target_id: str, relationship: Optional[str] = None):
    """
    Remove links between two memories.
    
    Examples:
        mesh-os memory unlink memory-id-1 memory-id-2
        mesh-os memory unlink memory-id-1 memory-id-2 -r related_to
    """
    try:
        client = get_client()
        if client.unlink_memories(source_id, target_id, relationship):
            console.print(f"[green]✓[/] Removed link(s) between memories")
        else:
            console.print("[yellow]No matching links found[/]")
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")

@memory.command()
@click.argument("memory_id", callback=validate_uuid)
@click.argument("content")
@click.option("--metadata", "-m", help="Updated metadata as JSON")
@click.option("--no-version", is_flag=True, help="Don't create a version link to the previous memory")
def update(memory_id: str, content: str, metadata: Optional[str] = None, no_version: bool = False):
    """
    Update a memory's content and optionally create a version link.
    
    Examples:
        mesh-os memory update memory-id "Updated content"
        mesh-os memory update memory-id "Updated content" -m '{"confidence": 0.9}'
        mesh-os memory update memory-id "Updated content" --no-version
    """
    try:
        client = get_client()
        metadata_dict = validate_metadata(metadata)
        new_memory = client.update_memory(
            memory_id=memory_id,
            content=content,
            metadata=metadata_dict,
            create_version_edge=not no_version
        )
        console.print(f"[green]✓[/] Created new version with ID: {new_memory.id}")
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")

@memory.command()
@click.argument("memory_id", callback=validate_uuid)
@click.option("--relationship", "-r", help="Filter by relationship type")
@click.option("--depth", "-d", default=1, help="Maximum depth to traverse")
def connections(memory_id: str, relationship: Optional[str] = None, depth: int = 1):
    """
    View memories connected to the given memory.
    
    Examples:
        mesh-os memory connections memory-id
        mesh-os memory connections memory-id -r version_of
        mesh-os memory connections memory-id -d 2
    """
    try:
        client = get_client()
        edges = client.get_connected_memories(memory_id, relationship, depth)
        
        if not edges:
            console.print("[yellow]No connected memories found[/]")
            return
        
        console.print(f"\n[green]Found {len(edges)} connections:[/]\n")
        for edge in edges:
            console.print(Panel(
                f"[blue]Source:[/] {edge['source_id']}\n"
                f"[blue]Target:[/] {edge['target_id']}\n"
                f"[blue]Relationship:[/] {edge['relationship']}\n"
                f"[blue]Weight:[/] {edge['weight']}\n"
                f"[blue]Depth:[/] {edge['depth']}",
                title="Memory Connection",
                border_style="blue"
            ))
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")

@cli.command()
@click.argument("project_name")
def create(project_name: str):
    """Create a new MeshOS project."""
    project_dir = Path.cwd() / project_name
    
    if project_dir.exists():
        console.print(f"[red]Error:[/] Directory {project_name} already exists")
        return
    
    # Create project
    console.print(Panel(
        f"Creating new project: [blue]{project_name}[/]\n\n"
        "This will set up:\n"
        "• PostgreSQL with pgvector for semantic search\n"
        "• Hasura GraphQL API\n"
        "• Example code and configuration",
        title="MeshOS Setup",
        border_style="blue"
    ))
    
    # Create project directory
    project_dir.mkdir(parents=True)
    
    # Copy templates
    with console.status("[bold]Setting up project files...", spinner="dots"):
        shutil.copytree(TEMPLATES_DIR / "hasura", project_dir / "hasura")
        shutil.copy(TEMPLATES_DIR / "docker-compose.yml", project_dir)
        
        # Create example script
        examples_dir = project_dir / "examples"
        examples_dir.mkdir()
        shutil.copy(TEMPLATES_DIR / "examples/simple_example.py", examples_dir / "example.py")
        
        # Create .env file
        env_file = project_dir / ".env"
        shutil.copy(TEMPLATES_DIR / ".env.example", env_file)
    
    console.print("\n[green]✓[/] Project files created")
    
    # Set up OpenAI API key
    console.print("\n[bold]Configuration[/]")
    has_api_key = setup_openai_key(env_file)  # Note: We're using project_dir/.env here
    
    # Show next steps
    console.print(Panel(
        "Next steps:\n\n"
        f"1. [green]cd {project_name}[/]\n"
        "2. [green]mesh-os up[/] to start the services"
        + ("" if has_api_key else "\n3. Add your [yellow]OPENAI_API_KEY[/] to [blue].env[/]"),
        title="Project Created",
        border_style="green"
    ))

@cli.command()
def up():
    """Start MeshOS services."""
    if not Path("docker-compose.yml").exists():
        console.print("[red]Error:[/] docker-compose.yml not found. Are you in a MeshOS project directory?")
        return
    
    # Load environment from current directory
    load_env()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        if not setup_openai_key(Path(".env")):
            console.print("\n[red]Error:[/] OpenAI API key is required to start services")
            return
    
    with console.status("[bold]Starting MeshOS services...", spinner="dots"):
        # First, ensure everything is stopped and volumes are clean
        subprocess.run(["docker", "compose", "down", "-v"], capture_output=True)
        
        # Start all services and capture output
        result = subprocess.run(["docker", "compose", "up", "-d"], capture_output=True, text=True)
        if result.returncode != 0:
            console.print("[red]Error starting services:[/]")
            console.print(result.stderr)
            return
    
    # Verify containers are actually running
    with console.status("[bold]Verifying services are running...", spinner="dots"):
        result = subprocess.run(["docker", "compose", "ps", "--format", "json"], capture_output=True, text=True)
        if result.returncode != 0:
            console.print("[red]Error checking service status:[/]")
            console.print(result.stderr)
            return
        
        # Check if both services are running
        running_services = subprocess.run(
            ["docker", "compose", "ps", "--services", "--filter", "status=running"],
            capture_output=True,
            text=True
        ).stdout.strip().split('\n')
        
        expected_services = {'postgres', 'hasura'}
        missing_services = expected_services - set(running_services)
        
        if missing_services:
            console.print(f"[red]Error:[/] The following services failed to start: {', '.join(missing_services)}")
            console.print("\nContainer logs:")
            for service in missing_services:
                console.print(f"\n[bold blue]{service} logs:[/]")
                subprocess.run(["docker", "compose", "logs", service])
            return
    
    # Wait for services to be ready with better feedback
    console.print("\n[yellow]Waiting for services to be ready...[/]")
    
    # Wait for PostgreSQL with timeout
    with console.status("[bold]Waiting for PostgreSQL...", spinner="dots"):
        postgres_ready = False
        for i in range(30):  # Try for 30 seconds
            try:
                result = subprocess.run(
                    ["docker", "compose", "exec", "-T", "postgres", "pg_isready", "-U", "postgres"],
                    capture_output=True
                )
                if result.returncode == 0:
                    postgres_ready = True
                    break
            except Exception as e:
                pass
            time.sleep(1)
        
        if not postgres_ready:
            console.print("[red]Error:[/] PostgreSQL failed to become ready in time")
            console.print("\nPostgreSQL logs:")
            subprocess.run(["docker", "compose", "logs", "postgres"])
            return
    
    # Wait for Hasura with timeout
    with console.status("[bold]Waiting for Hasura...", spinner="dots"):
        hasura_ready = False
        for i in range(30):  # Try for 30 seconds
            try:
                result = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", 
                     "-H", f"X-Hasura-Admin-Secret: {os.getenv('HASURA_ADMIN_SECRET', 'meshos')}", 
                     "http://localhost:8080/healthz"],
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip() == "200":
                    hasura_ready = True
                    break
            except Exception as e:
                pass
            time.sleep(1)
        
        if not hasura_ready:
            console.print("[red]Error:[/] Hasura failed to become ready in time")
            console.print("\nHasura logs:")
            subprocess.run(["docker", "compose", "logs", "hasura"])
            return
    
    # Run database migrations
    console.print("\n[yellow]Running database migrations...[/]")
    try:
        # Apply SQL migrations first
        with console.status("[bold]Applying SQL migrations...", spinner="dots"):
            migrations_dir = Path("hasura/migrations/default")
            if not migrations_dir.exists():
                console.print("[red]Error:[/] No migrations directory found at", migrations_dir)
                return
            
            # Get all migration directories in order
            migration_dirs = sorted([d for d in migrations_dir.iterdir() if d.is_dir()])
            if not migration_dirs:
                console.print("[red]Error:[/] No migration directories found in", migrations_dir)
                return
            
            # First create the hdb_catalog schema if it doesn't exist
            schema_result = subprocess.run(
                ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "mesh_os", "-c", 
                 "CREATE SCHEMA IF NOT EXISTS hdb_catalog;"],
                check=True,
                capture_output=True,
                text=True
            )
            if schema_result.returncode != 0:
                console.print("[red]Error creating hdb_catalog schema:[/]")
                console.print(schema_result.stderr)
                return
            
            # Apply each migration in order
            for migration_dir in migration_dirs:
                migration_file = migration_dir / "up.sql"
                if not migration_file.exists():
                    console.print(f"[yellow]Warning:[/] No up.sql found in {migration_dir}")
                    continue
                
                console.print(f"[blue]Applying migration:[/] {migration_dir.name}")
                console.print("[blue]Migration SQL preview:[/]")
                console.print(migration_file.read_text())
                
                # Run the migration
                result = subprocess.run(
                    ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "mesh_os", 
                     "-v", "ON_ERROR_STOP=1", "-a"],
                    input=migration_file.read_text(),
                    shell=False,
                    capture_output=True,
                    text=True
                )
                
                # Always show the output for debugging
                if result.stdout:
                    console.print("[blue]Migration output:[/]")
                    console.print(result.stdout)
                
                if result.stderr:
                    console.print("[yellow]Migration warnings/errors:[/]")
                    console.print(result.stderr)
                
                if result.returncode != 0:
                    console.print(f"[red]Error applying migration {migration_dir.name}[/]")
                    return
            
            # Verify the search_memories function was created with the latest version
            verify_result = subprocess.run(
                ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "mesh_os", "-c",
                 "SELECT proname, proargnames FROM pg_proc WHERE proname = 'search_memories';"],
                capture_output=True,
                text=True
            )
            
            if "search_memories" not in verify_result.stdout:
                console.print("[red]Warning:[/] search_memories function was not found after migrations")
                console.print("[blue]Attempting to verify what went wrong...[/]")
                
                # Check if the function exists with different parameters
                check_func = subprocess.run(
                    ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "mesh_os", "-c",
                     "\\df search_memories"],
                    capture_output=True,
                    text=True
                )
                console.print("[yellow]Function details:[/]")
                console.print(check_func.stdout)
            else:
                console.print("[green]✓[/] search_memories function created successfully")
            
            console.print("[green]✓[/] SQL migrations completed")
        
        # Apply Hasura metadata
        with console.status("[bold]Applying Hasura metadata...", spinner="dots"):
            metadata_dir = Path("hasura/metadata")
            if metadata_dir.exists():
                # Clear existing metadata
                result = subprocess.run(
                    ["curl", "-s", "-X", "POST", 
                     "-H", "Content-Type: application/json",
                     "-H", f"X-Hasura-Admin-Secret: {os.getenv('HASURA_ADMIN_SECRET', 'meshos')}",
                     "-d", '{"type":"clear_metadata","args":{}}',
                     "http://localhost:8080/v1/metadata"],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    console.print("[red]Error clearing metadata:[/]", result.stderr)
                    return

                # Create the default source
                source_payload = {
                    "type": "pg_add_source",
                    "args": {
                        "name": "default",
                        "configuration": {
                            "connection_info": {
                                "database_url": {
                                    "from_env": "HASURA_GRAPHQL_DATABASE_URL"
                                },
                                "isolation_level": "read-committed",
                                "use_prepared_statements": True
                            }
                        }
                    }
                }
                
                result = subprocess.run(
                    ["curl", "-s", "-X", "POST",
                     "-H", "Content-Type: application/json",
                     "-H", f"X-Hasura-Admin-Secret: {os.getenv('HASURA_ADMIN_SECRET', 'meshos')}",
                     "-d", json.dumps(source_payload),
                     "http://localhost:8080/v1/metadata"],
                    capture_output=True,
                    text=True
                )
                
                # Print the response for debugging
                if result.stdout:
                    try:
                        response = json.loads(result.stdout)
                        if "error" in response and "already exists" not in response.get("error", ""):
                            console.print("[red]Error creating source:[/]", json.dumps(response, indent=2))
                            return
                    except json.JSONDecodeError:
                        console.print("[red]Error parsing response:[/]", result.stdout)
                        return
                
                # Track specific tables and set up relationships
                track_tables_payload = {
                    "type": "bulk",
                    "args": [
                        {
                            "type": "pg_track_table",
                            "args": {
                                "source": "default",
                                "schema": "public",
                                "name": "agents"
                            }
                        },
                        {
                            "type": "pg_track_table",
                            "args": {
                                "source": "default",
                                "schema": "public",
                                "name": "memories"
                            }
                        },
                        {
                            "type": "pg_track_table",
                            "args": {
                                "source": "default",
                                "schema": "public",
                                "name": "memory_edges"
                            }
                        },
                        {
                            "type": "pg_track_table",
                            "args": {
                                "source": "default",
                                "schema": "public",
                                "name": "memories_with_similarity"
                            }
                        },
                        {
                            "type": "pg_track_table",
                            "args": {
                                "source": "default",
                                "schema": "public",
                                "name": "search_results_with_similarity"
                            }
                        },
                        {
                            "type": "pg_track_table",
                            "args": {
                                "source": "default",
                                "schema": "public",
                                "name": "entities"
                            }
                        },
                        {
                            "type": "pg_track_table",
                            "args": {
                                "source": "default",
                                "schema": "public",
                                "name": "entity_memory_links"
                            }
                        },
                        {
                            "type": "pg_track_table",
                            "args": {
                                "source": "default",
                                "schema": "public",
                                "name": "workflows"
                            }
                        },
                        {
                            "type": "pg_track_function",
                            "args": {
                                "function": {
                                    "schema": "public",
                                    "name": "search_memories"
                                },
                                "source": "default",
                                "configuration": {
                                    "exposed_as": "query",
                                    "arguments": [
                                        {
                                            "name": "args",
                                            "type": "search_memories_args!"
                                        }
                                    ]
                                },
                                "comment": "Function for semantic search of memories with similarity scores"
                            }
                        },
                        {
                            "type": "pg_track_function",
                            "args": {
                                "function": {
                                    "schema": "public",
                                    "name": "search_memories_and_entities"
                                },
                                "source": "default",
                                "configuration": {
                                    "exposed_as": "query"
                                },
                                "comment": "Function for combined semantic search of memories and entities"
                            }
                        },
                        {
                            "type": "pg_create_array_relationship",
                            "args": {
                                "table": {
                                    "schema": "public",
                                    "name": "agents"
                                },
                                "name": "memories",
                                "source": "default",
                                "using": {
                                    "foreign_key_constraint_on": {
                                        "column": "agent_id",
                                        "table": {
                                            "schema": "public",
                                            "name": "memories"
                                        }
                                    }
                                }
                            }
                        },
                        {
                            "type": "pg_create_object_relationship",
                            "args": {
                                "table": {
                                    "schema": "public",
                                    "name": "memories"
                                },
                                "name": "agent",
                                "source": "default",
                                "using": {
                                    "foreign_key_constraint_on": "agent_id"
                                }
                            }
                        },
                        {
                            "type": "pg_create_array_relationship",
                            "args": {
                                "table": {
                                    "schema": "public",
                                    "name": "memories"
                                },
                                "name": "incoming_edges",
                                "source": "default",
                                "using": {
                                    "foreign_key_constraint_on": {
                                        "column": "target_memory",
                                        "table": {
                                            "schema": "public",
                                            "name": "memory_edges"
                                        }
                                    }
                                }
                            }
                        },
                        {
                            "type": "pg_create_array_relationship",
                            "args": {
                                "table": {
                                    "schema": "public",
                                    "name": "memories"
                                },
                                "name": "outgoing_edges",
                                "source": "default",
                                "using": {
                                    "foreign_key_constraint_on": {
                                        "column": "source_memory",
                                        "table": {
                                            "schema": "public",
                                            "name": "memory_edges"
                                        }
                                    }
                                }
                            }
                        },
                        {
                            "type": "pg_create_array_relationship",
                            "args": {
                                "table": {
                                    "schema": "public",
                                    "name": "memories"
                                },
                                "name": "entity_links",
                                "source": "default",
                                "using": {
                                    "foreign_key_constraint_on": {
                                        "column": "memory_id",
                                        "table": {
                                            "schema": "public",
                                            "name": "entity_memory_links"
                                        }
                                    }
                                }
                            }
                        },
                        {
                            "type": "pg_create_array_relationship",
                            "args": {
                                "table": {
                                    "schema": "public",
                                    "name": "entities"
                                },
                                "name": "memory_links",
                                "source": "default",
                                "using": {
                                    "foreign_key_constraint_on": {
                                        "column": "entity_id",
                                        "table": {
                                            "schema": "public",
                                            "name": "entity_memory_links"
                                        }
                                    }
                                }
                            }
                        },
                        {
                            "type": "pg_create_object_relationship",
                            "args": {
                                "table": {
                                    "schema": "public",
                                    "name": "entity_memory_links"
                                },
                                "name": "entity",
                                "source": "default",
                                "using": {
                                    "foreign_key_constraint_on": "entity_id"
                                }
                            }
                        },
                        {
                            "type": "pg_create_object_relationship",
                            "args": {
                                "table": {
                                    "schema": "public",
                                    "name": "entity_memory_links"
                                },
                                "name": "memory",
                                "source": "default",
                                "using": {
                                    "foreign_key_constraint_on": "memory_id"
                                }
                            }
                        },
                        {
                            "type": "pg_create_object_relationship",
                            "args": {
                                "table": {
                                    "schema": "public",
                                    "name": "memory_edges"
                                },
                                "name": "source",
                                "source": "default",
                                "using": {
                                    "foreign_key_constraint_on": "source_memory"
                                }
                            }
                        },
                        {
                            "type": "pg_create_object_relationship",
                            "args": {
                                "table": {
                                    "schema": "public",
                                    "name": "memory_edges"
                                },
                                "name": "target",
                                "source": "default",
                                "using": {
                                    "foreign_key_constraint_on": "target_memory"
                                }
                            }
                        },
                        {
                            "type": "pg_create_object_relationship",
                            "args": {
                                "table": {
                                    "schema": "public",
                                    "name": "memories_with_similarity"
                                },
                                "name": "agent",
                                "source": "default",
                                "using": {
                                    "manual_configuration": {
                                        "remote_table": {
                                            "schema": "public",
                                            "name": "agents"
                                        },
                                        "column_mapping": {
                                            "agent_id": "id"
                                        }
                                    }
                                }
                            }
                        }
                    ]
                }
                
                result = subprocess.run(
                    ["curl", "-s", "-X", "POST",
                     "-H", "Content-Type: application/json",
                     "-H", f"X-Hasura-Admin-Secret: {os.getenv('HASURA_ADMIN_SECRET', 'meshos')}",
                     "-d", json.dumps(track_tables_payload),
                     "http://localhost:8080/v1/metadata"],
                    capture_output=True,
                    text=True
                )
                
                # Print the response for debugging
                if result.stdout:
                    try:
                        response = json.loads(result.stdout)
                        if "error" in response and not all(e in response.get("error", "") for e in ["already exists", "already tracked"]):
                            console.print("[red]Error tracking tables:[/]", json.dumps(response, indent=2))
                            return
                    except json.JSONDecodeError:
                        console.print("[red]Error parsing response:[/]", result.stdout)
                        return
                
                # Reload metadata
                result = subprocess.run(
                    ["curl", "-s", "-X", "POST",
                     "-H", "Content-Type: application/json",
                     "-H", f"X-Hasura-Admin-Secret: {os.getenv('HASURA_ADMIN_SECRET', 'meshos')}",
                     "-d", '{"type":"reload_metadata","args":{"reload_remote_schemas":true}}',
                     "http://localhost:8080/v1/metadata"],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    console.print("[red]Error reloading metadata:[/]", result.stderr)
                    return
                
                console.print("[green]✓[/] Hasura metadata applied successfully")
            else:
                console.print("[yellow]Warning:[/] No Hasura metadata found at", metadata_dir)
    
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error during migrations:[/] {str(e)}")
        console.print("\nYou can check the logs with: [blue]docker compose logs[/]")
        return
    
    hasura_port = os.getenv("HASURA_PORT", "8080")
    console_enabled = os.getenv("HASURA_ENABLE_CONSOLE", "true").lower() == "true"
    
    console.print(Panel(
        "[green]✓[/] Services started successfully!\n\n"
        "Services are now available at:\n\n"
        f"[blue]• GraphQL API:[/] http://localhost:{hasura_port}/v1/graphql\n"
        + (f"[blue]• Hasura Console:[/] http://localhost:{hasura_port}/console\n" if console_enabled else "")
        + "\nYou can now use the Python SDK or CLI to interact with your memory system.",
        title="Services Started",
        border_style="green"
    ))

@cli.command()
def down():
    """Roll back MeshOS services and migrations."""
    if not Path("docker-compose.yml").exists():
        console.print("[red]Error:[/] docker-compose.yml not found. Are you in a MeshOS project directory?")
        return
    
    # Load environment from current directory
    load_env()
    
    try:
        # Roll back migrations in reverse order
        with console.status("[bold]Rolling back migrations...", spinner="dots"):
            migrations_dir = Path("hasura/migrations/default")
            if migrations_dir.exists():
                # Get all migration directories in reverse order
                migration_dirs = sorted([d for d in migrations_dir.iterdir() if d.is_dir()], reverse=True)
                
                for migration_dir in migration_dirs:
                    down_file = migration_dir / "down.sql"
                    if not down_file.exists():
                        console.print(f"[yellow]Warning:[/] No down.sql found in {migration_dir}")
                        continue
                    
                    console.print(f"[blue]Rolling back migration:[/] {migration_dir.name}")
                    console.print("[blue]Rollback SQL preview:[/]")
                    console.print(down_file.read_text())
                    
                    # Run the rollback
                    result = subprocess.run(
                        ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "mesh_os", 
                         "-v", "ON_ERROR_STOP=1", "-a"],
                        input=down_file.read_text(),
                        shell=False,
                        capture_output=True,
                        text=True
                    )
                    
                    # Always show the output for debugging
                    if result.stdout:
                        console.print("[blue]Rollback output:[/]")
                        console.print(result.stdout)
                    
                    if result.stderr:
                        console.print("[yellow]Rollback warnings/errors:[/]")
                        console.print(result.stderr)
                    
                    if result.returncode != 0:
                        console.print(f"[red]Error rolling back migration {migration_dir.name}[/]")
                        return
                
                console.print("[green]✓[/] Migrations rolled back successfully")
        
        # Stop all services
        with console.status("[bold]Stopping services...", spinner="dots"):
            subprocess.run(["docker", "compose", "down", "-v"], capture_output=True)
        
        console.print(Panel(
            "[green]✓[/] Services stopped and migrations rolled back successfully!",
            title="Services Stopped",
            border_style="green"
        ))
    
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error during rollback:[/] {str(e)}")
        console.print("\nYou can check the logs with: [blue]docker compose logs[/]")
        return

@cli.command("up:remote")
@click.option("--url", required=True, help="URL of the Hasura instance (e.g. https://your-instance.hasura.app)")
@click.option("--admin-secret", required=True, help="Admin secret for the Hasura instance")
@click.option("--clean", is_flag=True, help="Clear existing metadata before deploying")
def remote_up(url: str, admin_secret: str, clean: bool):
    """Deploy metadata and migrations to an external Hasura instance."""
    if not Path("hasura/metadata").exists():
        console.print("[red]Error:[/] No Hasura metadata directory found. Are you in a MeshOS project directory?")
        return

    # Normalize URL by removing trailing slash
    url = url.rstrip("/")
    base_url = f"{url}/v1/metadata"

    try:
        # Test connection to Hasura instance
        with console.status("[bold]Testing connection to Hasura instance...", spinner="dots"):
            result = subprocess.run(
                ["curl", "-s", "-X", "GET",
                 "-H", f"X-Hasura-Admin-Secret: {admin_secret}",
                 "-H", "Content-Type: application/json",
                 f"{url}/v1/version"],
                capture_output=True,
                text=True
            )
            
            try:
                response = json.loads(result.stdout)
                if "version" in response:
                    console.print(f"[green]✓[/] Connected to Hasura version: {response['version']}")
                else:
                    console.print("[red]Error:[/] Invalid response from Hasura instance")
                    console.print(f"Response: {result.stdout}")
                    return
            except json.JSONDecodeError:
                console.print("[red]Error:[/] Could not connect to Hasura instance")
                console.print(f"Response: {result.stdout}")
                if result.stderr:
                    console.print(f"Error details: {result.stderr}")
                return

        # Clear existing metadata if requested
        if clean:
            with console.status("[bold]Clearing existing metadata...", spinner="dots"):
                result = subprocess.run(
                    ["curl", "-s", "-X", "POST",
                     "-H", "Content-Type: application/json",
                     "-H", f"X-Hasura-Admin-Secret: {admin_secret}",
                     "-d", '{"type":"clear_metadata","args":{}}',
                     base_url],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    console.print("[red]Error clearing metadata:[/]", result.stderr)
                    return

        # Create the default source
        with console.status("[bold]Setting up database source...", spinner="dots"):
            source_payload = {
                "type": "pg_add_source",
                "args": {
                    "name": "default",
                    "configuration": {
                        "connection_info": {
                            "database_url": {
                                "from_env": "HASURA_GRAPHQL_DATABASE_URL"
                            },
                            "isolation_level": "read-committed",
                            "use_prepared_statements": True
                        }
                    }
                }
            }

            result = subprocess.run(
                ["curl", "-s", "-X", "POST",
                 "-H", "Content-Type: application/json",
                 "-H", f"X-Hasura-Admin-Secret: {admin_secret}",
                 "-d", json.dumps(source_payload),
                 base_url],
                capture_output=True,
                text=True
            )

            if result.stdout:
                try:
                    response = json.loads(result.stdout)
                    if "error" in response and "already exists" not in response.get("error", ""):
                        console.print("[red]Error creating source:[/]", json.dumps(response, indent=2))
                        return
                except json.JSONDecodeError:
                    console.print("[red]Error parsing response:[/]", result.stdout)
                    return

        # Track tables and set up relationships
        with console.status("[bold]Setting up tables and relationships...", spinner="dots"):
            track_tables_payload = {
                "type": "bulk",
                "args": [
                    {
                        "type": "pg_track_table",
                        "args": {
                            "source": "default",
                            "schema": "public",
                            "name": "agents"
                        }
                    },
                    {
                        "type": "pg_track_table",
                        "args": {
                            "source": "default",
                            "schema": "public",
                            "name": "memories"
                        }
                    },
                    {
                        "type": "pg_track_table",
                        "args": {
                            "source": "default",
                            "schema": "public",
                            "name": "memory_edges"
                        }
                    },
                    {
                        "type": "pg_track_table",
                        "args": {
                            "source": "default",
                            "schema": "public",
                            "name": "memories_with_similarity"
                        }
                    },
                    {
                        "type": "pg_track_table",
                        "args": {
                            "source": "default",
                            "schema": "public",
                            "name": "search_results_with_similarity"
                        }
                    },
                    {
                        "type": "pg_track_table",
                        "args": {
                            "source": "default",
                            "schema": "public",
                            "name": "entities"
                        }
                    },
                    {
                        "type": "pg_track_table",
                        "args": {
                            "source": "default",
                            "schema": "public",
                            "name": "entity_memory_links"
                        }
                    },
                    {
                        "type": "pg_track_table",
                        "args": {
                            "source": "default",
                            "schema": "public",
                            "name": "workflows"
                        }
                    },
                    {
                        "type": "pg_track_function",
                        "args": {
                            "function": {
                                "schema": "public",
                                "name": "search_memories"
                            },
                            "source": "default",
                            "configuration": {
                                "exposed_as": "query",
                                "arguments": [
                                    {
                                        "name": "args",
                                        "type": "search_memories_args!"
                                    }
                                ]
                            },
                            "comment": "Function for semantic search of memories with similarity scores"
                        }
                    },
                    {
                        "type": "pg_track_function",
                        "args": {
                            "function": {
                                "schema": "public",
                                "name": "search_memories_and_entities"
                            },
                            "source": "default",
                            "configuration": {
                                "exposed_as": "query"
                            },
                            "comment": "Function for combined semantic search of memories and entities"
                        }
                    },
                    {
                        "type": "pg_create_array_relationship",
                        "args": {
                            "table": {
                                "schema": "public",
                                "name": "agents"
                            },
                            "name": "memories",
                            "source": "default",
                            "using": {
                                "foreign_key_constraint_on": {
                                    "column": "agent_id",
                                    "table": {
                                        "schema": "public",
                                        "name": "memories"
                                    }
                                }
                            }
                        }
                    },
                    {
                        "type": "pg_create_object_relationship",
                        "args": {
                            "table": {
                                "schema": "public",
                                "name": "memories"
                            },
                            "name": "agent",
                            "source": "default",
                            "using": {
                                "foreign_key_constraint_on": "agent_id"
                            }
                        }
                    },
                    {
                        "type": "pg_create_array_relationship",
                        "args": {
                            "table": {
                                "schema": "public",
                                "name": "memories"
                            },
                            "name": "incoming_edges",
                            "source": "default",
                            "using": {
                                "foreign_key_constraint_on": {
                                    "column": "target_memory",
                                    "table": {
                                        "schema": "public",
                                        "name": "memory_edges"
                                    }
                                }
                            }
                        }
                    },
                    {
                        "type": "pg_create_array_relationship",
                        "args": {
                            "table": {
                                "schema": "public",
                                "name": "memories"
                            },
                            "name": "outgoing_edges",
                            "source": "default",
                            "using": {
                                "foreign_key_constraint_on": {
                                    "column": "source_memory",
                                    "table": {
                                        "schema": "public",
                                        "name": "memory_edges"
                                    }
                                }
                            }
                        }
                    },
                    {
                        "type": "pg_create_array_relationship",
                        "args": {
                            "table": {
                                "schema": "public",
                                "name": "memories"
                            },
                            "name": "entity_links",
                            "source": "default",
                            "using": {
                                "foreign_key_constraint_on": {
                                    "column": "memory_id",
                                    "table": {
                                        "schema": "public",
                                        "name": "entity_memory_links"
                                    }
                                }
                            }
                        }
                    },
                    {
                        "type": "pg_create_array_relationship",
                        "args": {
                            "table": {
                                "schema": "public",
                                "name": "entities"
                            },
                            "name": "memory_links",
                            "source": "default",
                            "using": {
                                "foreign_key_constraint_on": {
                                    "column": "entity_id",
                                    "table": {
                                        "schema": "public",
                                        "name": "entity_memory_links"
                                    }
                                }
                            }
                        }
                    },
                    {
                        "type": "pg_create_object_relationship",
                        "args": {
                            "table": {
                                "schema": "public",
                                "name": "entity_memory_links"
                            },
                            "name": "entity",
                            "source": "default",
                            "using": {
                                "foreign_key_constraint_on": "entity_id"
                            }
                        }
                    },
                    {
                        "type": "pg_create_object_relationship",
                        "args": {
                            "table": {
                                "schema": "public",
                                "name": "entity_memory_links"
                            },
                            "name": "memory",
                            "source": "default",
                            "using": {
                                "foreign_key_constraint_on": "memory_id"
                            }
                        }
                    },
                    {
                        "type": "pg_create_object_relationship",
                        "args": {
                            "table": {
                                "schema": "public",
                                "name": "memory_edges"
                            },
                            "name": "source",
                            "source": "default",
                            "using": {
                                "foreign_key_constraint_on": "source_memory"
                            }
                        }
                    },
                    {
                        "type": "pg_create_object_relationship",
                        "args": {
                            "table": {
                                "schema": "public",
                                "name": "memory_edges"
                            },
                            "name": "target",
                            "source": "default",
                            "using": {
                                "foreign_key_constraint_on": "target_memory"
                            }
                        }
                    },
                    {
                        "type": "pg_create_object_relationship",
                        "args": {
                            "table": {
                                "schema": "public",
                                "name": "memories_with_similarity"
                            },
                            "name": "agent",
                            "source": "default",
                            "using": {
                                "manual_configuration": {
                                    "remote_table": {
                                        "schema": "public",
                                        "name": "agents"
                                    },
                                    "column_mapping": {
                                        "agent_id": "id"
                                    }
                                }
                            }
                        }
                    }
                ]
            }

            result = subprocess.run(
                ["curl", "-s", "-X", "POST",
                 "-H", "Content-Type: application/json",
                 "-H", f"X-Hasura-Admin-Secret: {admin_secret}",
                 "-d", json.dumps(track_tables_payload),
                 base_url],
                capture_output=True,
                text=True
            )

            if result.stdout:
                try:
                    response = json.loads(result.stdout)
                    if "error" in response and not all(e in response.get("error", "") for e in ["already exists", "already tracked"]):
                        console.print("[red]Error tracking tables:[/]", json.dumps(response, indent=2))
                        return
                except json.JSONDecodeError:
                    console.print("[red]Error parsing response:[/]", result.stdout)
                    return

        # Reload metadata
        with console.status("[bold]Reloading metadata...", spinner="dots"):
            result = subprocess.run(
                ["curl", "-s", "-X", "POST",
                 "-H", "Content-Type: application/json",
                 "-H", f"X-Hasura-Admin-Secret: {admin_secret}",
                 "-d", '{"type":"reload_metadata","args":{"reload_remote_schemas":true}}',
                 base_url],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                console.print("[red]Error reloading metadata:[/]", result.stderr)
                return

        console.print(Panel(
            "[green]✓[/] Successfully deployed metadata to external Hasura instance!\n\n"
            f"[blue]• GraphQL API:[/] {url}/v1/graphql\n"
            f"[blue]• Hasura Console:[/] {url}/console",
            title="Deployment Complete",
            border_style="green"
        ))

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error during deployment:[/] {str(e)}")
        return
    except Exception as e:
        console.print(f"[red]Unexpected error:[/] {str(e)}")
        return

if __name__ == "__main__":
    cli() 