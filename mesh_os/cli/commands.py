import json
import sys
import uuid
import click

from mesh_os.core.client import get_client, InvalidSlugError

@agent.command()
@click.argument("name")
@click.option("--description", required=True, help="Agent description")
@click.option("--metadata", required=True, help="Agent metadata as JSON string")
@click.option("--slug", required=True, help="Unique slug for the agent")
def register(name: str, description: str, metadata: str, slug: str):
    """Register a new agent."""
    try:
        metadata_dict = json.loads(metadata)
        agent = get_client().register_agent(
            name=name,
            description=description,
            metadata=metadata_dict,
            slug=slug
        )
        click.echo(f"✓ Agent registered with ID: {agent.id} (slug: {agent.slug.strip()})")
    except InvalidSlugError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    except json.JSONDecodeError:
        click.echo("Error: Invalid JSON format for metadata", err=True)
        sys.exit(1)

@agent.command()
@click.argument("identifier")
def unregister(identifier: str):
    """Unregister an agent by UUID or slug."""
    client = get_client()
    
    # First try to get agent by slug
    try:
        agent = client.get_agent_by_slug(identifier)
        if agent:
            client.unregister_agent(agent.id)
            click.echo(f"✓ Agent unregistered (slug: {agent.slug})")
            return
    except Exception:
        pass
    
    # If not found by slug, validate UUID format
    try:
        uuid.UUID(identifier)
    except ValueError:
        click.echo("Error: Invalid UUID format", err=True)
        sys.exit(1)
    
    # If UUID is valid, try to unregister
    try:
        client.unregister_agent(identifier)
        click.echo("✓ Agent unregistered")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1) 