# PropsOS v0.1.0 - Initial Release

PropsOS is a lightweight multi-agent memory system with semantic search capabilities.

## Features
- 🤖 Agent Management (register/unregister agents)
- 🧠 Memory Storage with Semantic Search
- 🔍 Advanced Filtering Support
- 🚀 Easy-to-use Python SDK
- 🛠️ CLI Tool for Project Setup

## Installation
```bash
pip install props-os
```

## Quick Start
```python
from props_os import PropsOS

# Initialize client
props = PropsOS(api_key="your-api-key")

# Register an agent
agent = props.register_agent(
    name="Assistant",
    description="A helpful AI assistant",
    metadata={"capabilities": ["chat", "research"]}
)

# Store a memory
memory = props.remember(
    content="The user asked about Python programming",
    agent_id=agent.id,
    metadata={"type": "conversation"}
)

# Search memories
memories = props.recall(
    query="What did the user ask about?",
    agent_id=agent.id
)
```

## Requirements
- Python 3.9+
- OpenAI API key
- Docker (for local development)

## Documentation
See the [README.md](https://github.com/Props-Labs/props-os/blob/main/README.md) for full documentation. 