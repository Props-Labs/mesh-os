"""
CLI interface for PropsOS.
"""
import os
import shutil
from pathlib import Path
from typing import Optional
import subprocess
import time
import json

import click
from dotenv import load_dotenv, find_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import print as rprint

from props_os.core.client import PropsOS

console = Console()

def load_env():
    """Load environment variables from .env file in current directory."""
    env_file = find_dotenv(usecwd=True)
    if env_file:
        load_dotenv(env_file)
        return True
    return False

def get_client():
    """Get a configured PropsOS client."""
    # Try to load environment from current directory
    load_env()
    
    hasura_url = os.getenv("HASURA_URL", "http://localhost:8080/v1/graphql")
    hasura_admin_secret = os.getenv("HASURA_ADMIN_SECRET", "myhasurasecret")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        if not setup_openai_key(Path(".env")):
            raise ValueError("OpenAI API key is required")
        # Reload environment after setting up the key
        load_env()
        openai_api_key = os.getenv("OPENAI_API_KEY")
    
    return PropsOS(
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
        "PropsOS uses OpenAI's API for generating embeddings.\n"
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
        "\n[yellow]Note:[/] You'll need to set OPENAI_API_KEY in your .env file before using PropsOS"
    )
    return False

# Get the package root directory
PACKAGE_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PACKAGE_ROOT / "templates"

@click.group()
def cli():
    """PropsOS CLI - Manage your agent memory system."""
    pass

@cli.group()
def agent():
    """Manage agents."""
    pass

@agent.command()
@click.argument("name")
@click.option("--description", "-d", help="Agent description")
@click.option("--metadata", "-m", help="Agent metadata as JSON")
def register(name: str, description: Optional[str] = None, metadata: Optional[str] = None):
    """Register a new agent."""
    try:
        client = get_client()
        metadata_dict = json.loads(metadata) if metadata else None
        agent = client.register_agent(name, description, metadata_dict)
        console.print(f"[green]✓[/] Agent registered with ID: {agent.id}")
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")

@agent.command()
@click.argument("agent_id")
def unregister(agent_id: str):
    """Unregister an agent."""
    try:
        client = get_client()
        if client.unregister_agent(agent_id):
            console.print(f"[green]✓[/] Agent {agent_id} unregistered")
        else:
            console.print(f"[red]Error:[/] Agent {agent_id} not found")
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")

@cli.group()
def memory():
    """Manage memories."""
    pass

@memory.command()
@click.argument("content")
@click.option("--agent-id", "-a", help="Agent ID to associate with the memory")
@click.option("--metadata", "-m", help="Memory metadata as JSON")
def remember(content: str, agent_id: Optional[str] = None, metadata: Optional[str] = None):
    """Store a new memory."""
    try:
        client = get_client()
        metadata_dict = json.loads(metadata) if metadata else None
        memory = client.remember(content, agent_id, metadata_dict)
        console.print(f"[green]✓[/] Memory stored with ID: {memory.id}")
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")

@memory.command()
@click.argument("query")
@click.option("--agent-id", "-a", help="Filter memories by agent ID")
@click.option("--limit", "-l", default=5, help="Maximum number of results")
@click.option("--threshold", "-t", default=0.7, help="Similarity threshold (0-1)")
@click.option("--filter", "-f", multiple=True, help="Add metadata filters in format key=value or key.operator=value (e.g., type=note or confidence._gt=0.8)")
def recall(query: str, agent_id: Optional[str] = None, limit: int = 5, threshold: float = 0.7, filter: tuple = ()):
    """
    Search for similar memories with optional filters.
    
    Examples:
        props-os memory recall "What do you know about me?" -f type=note
        props-os memory recall "Important insights" -f confidence._gt=0.8 -f tags._contains=["important"]
        props-os memory recall "Recent updates" -f created_at._gte=2024-01-01
    """
    try:
        client = get_client()
        
        # Parse filters
        filters = {}
        for f in filter:
            if "=" not in f:
                console.print(f"[red]Error:[/] Invalid filter format: {f}")
                return
                
            key, value = f.split("=", 1)
            
            # Handle complex filters with operators
            if "._" in key:
                base_key, operator = key.split("._", 1)
                try:
                    # Try to parse as JSON for arrays and objects
                    parsed_value = json.loads(value)
                except json.JSONDecodeError:
                    # If not JSON, use as string
                    parsed_value = value
                filters[base_key] = {f"_{operator}": parsed_value}
            else:
                try:
                    # Try to parse as JSON for arrays and objects
                    parsed_value = json.loads(value)
                except json.JSONDecodeError:
                    # If not JSON, use as string
                    parsed_value = value
                filters[key] = parsed_value
        
        memories = client.recall(query, agent_id, limit, threshold, filters)
        if not memories:
            console.print("[yellow]No matching memories found[/]")
            return
        
        console.print(f"\n[green]Found {len(memories)} matching memories:[/]\n")
        for memory in memories:
            metadata_str = json.dumps(memory.metadata, indent=2) if memory.metadata else "None"
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
@click.argument("memory_id")
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

@cli.command()
@click.argument("project_name")
def create(project_name: str):
    """Create a new PropsOS project."""
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
        title="PropsOS Setup",
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
        "2. [green]props-os up[/] to start the services"
        + ("" if has_api_key else "\n3. Add your [yellow]OPENAI_API_KEY[/] to [blue].env[/]"),
        title="Project Created",
        border_style="green"
    ))

@cli.command()
def up():
    """Start PropsOS services."""
    if not Path("docker-compose.yml").exists():
        console.print("[red]Error:[/] docker-compose.yml not found. Are you in a PropsOS project directory?")
        return
    
    # Load environment from current directory
    load_env()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        if not setup_openai_key(Path(".env")):
            console.print("\n[red]Error:[/] OpenAI API key is required to start services")
            return
    
    with console.status("[bold]Starting PropsOS services...", spinner="dots"):
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
                     "-H", f"X-Hasura-Admin-Secret: {os.getenv('HASURA_ADMIN_SECRET', 'myhasurasecret')}", 
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
            migration_file = Path("hasura/migrations/default/1_init/up.sql")
            if migration_file.exists():
                # First create the hdb_catalog schema if it doesn't exist
                subprocess.run(
                    ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "props_os", "-c", 
                     "CREATE SCHEMA IF NOT EXISTS hdb_catalog;"],
                    check=True,
                    capture_output=True  # Capture output to prevent noise
                )
                
                # Then run the migrations by passing the file directly
                result = subprocess.run(
                    f"cat {migration_file} | docker compose exec -T postgres psql -U postgres -d props_os",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    console.print("[red]Error applying SQL migrations:[/]")
                    if result.stderr:
                        console.print(result.stderr)
                    if result.stdout:
                        console.print(result.stdout)
                    return
                console.print("[green]✓[/] SQL migrations applied successfully")
            else:
                console.print("[yellow]Warning:[/] No SQL migrations found at", migration_file)
        
        # Apply Hasura metadata
        with console.status("[bold]Applying Hasura metadata...", spinner="dots"):
            metadata_dir = Path("hasura/metadata")
            if metadata_dir.exists():
                # Clear existing metadata
                result = subprocess.run(
                    ["curl", "-s", "-X", "POST", 
                     "-H", "Content-Type: application/json",
                     "-H", f"X-Hasura-Admin-Secret: {os.getenv('HASURA_ADMIN_SECRET', 'myhasurasecret')}",
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
                     "-H", f"X-Hasura-Admin-Secret: {os.getenv('HASURA_ADMIN_SECRET', 'myhasurasecret')}",
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
                        }
                    ]
                }
                
                result = subprocess.run(
                    ["curl", "-s", "-X", "POST",
                     "-H", "Content-Type: application/json",
                     "-H", f"X-Hasura-Admin-Secret: {os.getenv('HASURA_ADMIN_SECRET', 'myhasurasecret')}",
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
                     "-H", f"X-Hasura-Admin-Secret: {os.getenv('HASURA_ADMIN_SECRET', 'myhasurasecret')}",
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
    """Stop PropsOS services."""
    if not Path("docker-compose.yml").exists():
        console.print("[red]Error:[/] docker-compose.yml not found. Are you in a PropsOS project directory?")
        return
    
    with console.status("[bold]Stopping PropsOS services...", spinner="dots"):
        subprocess.run(["docker", "compose", "down"], capture_output=True)
    console.print("[green]✓[/] Services stopped successfully")

if __name__ == "__main__":
    cli() 