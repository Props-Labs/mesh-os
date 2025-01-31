# VentureOS

A lightweight multi-agent memory system with vector search capabilities.

## Features

- Agent lifecycle management (register, deregister, status updates)
- Memory storage with optional vector embeddings
- Semantic search using pgvector
- GraphQL API via Hasura
- CLI for easy management
- Python SDK for programmatic access

## Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Poetry (for Python dependency management)

## Installation

1. Install the package using Poetry:

```bash
poetry install
```

2. Create a `.env` file with your configuration:

```bash
POSTGRES_PASSWORD=your_secure_password
HASURA_ADMIN_SECRET=your_secure_secret
POSTGRES_PORT=5432
HASURA_PORT=8080
```

3. Start the services:

```bash
# Copy the Docker Compose template
mkdir -p deploy
cp venture_os/templates/docker-compose.yml deploy/
cp -r venture_os/templates/migrations deploy/

# Start services
cd deploy
docker compose up -d
```

## Usage

### CLI Commands

Managing Agents:

```bash
# Register a new agent
venture-os agent register "MyAgent" --description "Test agent" --status "active"

# Update agent status
venture-os agent status <agent_id> "busy"

# Deregister an agent
venture-os agent deregister <agent_id>
```

Managing Memories:

```bash
# Add a memory
venture-os memory add "note" '{"text": "Hello world"}' --agent-id <agent_id>

# Delete a memory
venture-os memory delete <memory_id>
```

### Python SDK

```python
from venture_os.core.sdk import AgentMemorySDK

# Initialize SDK
sdk = AgentMemorySDK()

# Register an agent
agent = sdk.register_agent(
    name="MyAgent",
    description="Test agent",
    status="active"
)

# Add a memory
memory = sdk.add_memory(
    memory_type="note",
    data={"text": "Hello world"},
    agent_id=agent.id
)

# Search memories (with vector)
results = sdk.search_memories(
    query_vector=[0.1, 0.2, ...],  # 1536-dimensional vector
    limit=5,
    agent_id=agent.id  # Optional: filter by agent
)
```

## Development

1. Install development dependencies:

```bash
poetry install --with dev
```

2. Run tests:

```bash
poetry run pytest
```

3. Format code:

```bash
poetry run black venture_os tests
poetry run isort venture_os tests
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 