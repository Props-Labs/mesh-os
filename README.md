# MeshOS

A lightweight multi-agent memory system with vector search capabilities, built on PostgreSQL and Hasura.

## Features

- 🤖 Multi-agent system with lifecycle management
- 🧠 Vector-based memory storage using pgvector
- 🔍 Semantic search with advanced filtering
- 🚀 GraphQL API powered by Hasura
- 🛠️ Easy-to-use CLI
- 📚 Python SDK for seamless integration

## Quick Start

1. Install the package:
```bash
pip install mesh-os
```

2. Create a new project:
```bash
mesh-os create my-os
cd my-os
```

3. Add your OpenAI API key when prompted, or edit `.env`:
```bash
OPENAI_API_KEY=your_api_key_here
```

4. Start the services:
```bash
mesh-os up
```

That's it! Your MeshOS instance is now running with:
- PostgreSQL with pgvector at `localhost:5432`
- Hasura GraphQL API at `http://localhost:8080/v1/graphql`
- Hasura Console at `http://localhost:8080/console`

## Python SDK Usage

```python
from mesh_os import MeshOS

# Initialize the client
os = MeshOS()

# Register an agent
agent = os.register_agent(
    name="research-assistant",
    description="AI research assistant",
    metadata={
        "capabilities": ["research", "summarization"],
        "model": "gpt-4"
    }
)

# Store memories
memory = os.remember(
    content="The key insight from the paper is that transformer architectures...",
    agent_id=agent.id,
    metadata={
        "type": "research_note",
        "source": "arxiv:2312.12345",
        "confidence": 0.95,
        "tags": ["paper", "transformers", "important"]
    }
)

# Search memories with advanced filters
memories = os.recall(
    query="What were the key insights about transformers?",
    agent_id=agent.id,  # Optional: filter by agent
    limit=5,
    threshold=0.7,  # Similarity threshold
    filters={
        # Simple equality filter
        "type": "research_note",
        
        # Numeric comparisons
        "confidence": {"_gt": 0.8},
        
        # Date/time filters
        "created_at": {"_gte": "2024-01-01"},
        
        # Array operations
        "tags": {"_contains": ["important"]},
        
        # Nested JSON filters
        "metadata": {"_contains": {"source": "arxiv"}}
    }
)

# Delete a specific memory
os.forget(memory.id)

# Unregister an agent (and all their memories)
os.unregister_agent(agent.id)
```

## CLI Usage

```bash
# Agent Management
mesh-os agent register "assistant" \
    --description "Research assistant" \
    --metadata '{"model": "gpt-4"}'

mesh-os agent unregister <agent-id>

# Memory Management
mesh-os memory remember "Important insight..." \
    --agent-id <agent-id> \
    --metadata '{"type": "note", "tags": ["important"]}'

# Search with filters
mesh-os memory recall "What do you know?" \
    --agent-id <agent-id> \
    --limit 5 \
    --threshold 0.7 \
    --filter type=research_note \
    --filter 'confidence._gt=0.8' \
    --filter 'created_at._gte=2024-01-01' \
    --filter 'tags._contains=["important"]' \
    --filter 'metadata._contains={"source":"arxiv"}'

mesh-os memory forget <memory-id>
```

## Configuration

The `.env` file supports the following options:

```bash
# Required
OPENAI_API_KEY=your_api_key_here

# Optional (defaults shown)
POSTGRES_PASSWORD=mysecretpassword
HASURA_ADMIN_SECRET=meshos
POSTGRES_PORT=5432
HASURA_PORT=8080
HASURA_ENABLE_CONSOLE=true
```

## Architecture

MeshOS is built on:
- **PostgreSQL + pgvector**: For persistent storage and vector similarity search
- **Hasura**: For the GraphQL API and real-time subscriptions
- **OpenAI**: For generating embeddings (using `text-embedding-3-small`)
- **Python**: For the SDK and CLI

## Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mesh-os.git
cd mesh-os
```

2. Install dependencies:
```bash
poetry install
```

3. Run tests:
```bash
poetry run pytest
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) for details. 