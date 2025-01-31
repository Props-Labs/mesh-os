# MeshOS v0.1.0 - Initial Release

MeshOS is a lightweight multi-agent memory system for business, complete with vector search capabilities, built on PostgreSQL and Hasura.

## Features
- 🤖 Multi-agent system with lifecycle management
- 🧠 Vector-based memory storage using pgvector
- 🔍 Semantic search with advanced filtering
- 🌳 Rich taxonomy system for memory classification
- 🔗 Memory linking with relationship types
- 🚀 GraphQL API powered by Hasura
- 🛠️ Easy-to-use CLI
- 📚 Python SDK for seamless integration

## Core Components
- PostgreSQL + pgvector for persistent storage and vector similarity search
- Hasura for GraphQL API and real-time subscriptions
- OpenAI integration for embeddings (using text-embedding-3-small)

## Memory Taxonomy Support
- Data Types: KNOWLEDGE, ACTIVITY, DECISION, MEDIA
- Rich subtypes for each category (e.g., Research Papers, User Interactions, Reasoning, Images)
- Flexible metadata and tagging system
- Relationship-based memory linking

## Installation
```bash
pip install mesh-os
```

## Quick Start
```python
from mesh_os import MeshOS
from mesh_os.core.taxonomy import DataType, KnowledgeSubtype

# Initialize client
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

# Store memories with taxonomy
memory = os.remember(
    content="The key insight from the paper is...",
    agent_id=agent.id,
    metadata={
        "type": DataType.KNOWLEDGE,
        "subtype": KnowledgeSubtype.RESEARCH_PAPER,
        "confidence": 0.95,
        "tags": ["paper", "important"]
    }
)

# Search memories with advanced filters
memories = os.recall(
    query="What were the key insights?",
    agent_id=agent.id,
    limit=5,
    threshold=0.7,
    filters={
        "type": DataType.KNOWLEDGE,
        "confidence": {"_gt": 0.8}
    }
)
```

## Requirements
- Python 3.9+
- OpenAI API key
- Docker (for local development)

## Documentation
See the [README.md](https://github.com/Props-Labs/mesh-os/blob/main/README.md) for full documentation. 