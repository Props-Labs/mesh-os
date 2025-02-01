# MeshOS

**Multi-agent data operations for AI-powered businesses**

MeshOS is a **structured, opinionated memory system** designed to power **multi-agent ventures and autonomous business operations**. Unlike generic memory stores, MeshOS provides:

- **Multi-agent memory orchestration** – AI agents and humans share structured knowledge.
- **Rich taxonomy & classification** – Knowledge, activity, decision, and media hierarchies.
- **Graph-based relationships** – Versioned, linked memory across an evolving system.
- **Operational intelligence** – A path to **fully autonomous ventures** via structured agent collaboration.
- **Open-source and portable** – Built on **PostgreSQL**, **pgvector**, and **Hasura**, ensuring full portability and no vendor lock-in.

## 🚀 Why MeshOS?

**Most memory systems are just storage. MeshOS is an operational framework.**

It is **not** just a vector search tool—it is a **full-stack knowledge and activity management layer** for agent-driven businesses.

| Feature                      | MeshOS | Mem0 / Letta / Zep |
| ---------------------------- | ------ | ------------------ |
| **Multi-Agent Memory**       | ✅ Yes  | ❌ No               |
| **Structured Taxonomy**      | ✅ Yes  | ❌ No               |
| **Versioned Knowledge**      | ✅ Yes  | ❌ No               |
| **Semantic & Graph Search**  | ✅ Yes  | ✅ Partial          |
| **Business-Oriented**        | ✅ Yes  | ❌ No               |
| **Operational Intelligence** | ✅ Yes  | ❌ No               |
| **Open-Source & Portable**   | ✅ Yes  | ✅ Partial          |

**Who is MeshOS for?**

✅ **AI-powered ventures** – Businesses that need structured AI agents managing knowledge and decisions.\
✅ **Autonomous teams** – Multi-agent collaboration with structured memory and contextual understanding.\
✅ **Developers & enterprises** – Building AI-powered operational systems, not just memory stores.

## 🏗️ Core Features

✅ **AI-Driven Memory** – Store structured **knowledge, activities, decisions, and media**.\
✅ **Taxonomy & Classification** – Enforce hierarchical data models across agents.\
✅ **Multi-Agent Collaboration** – Agents operate independently, yet share structured memory.\
✅ **Versioned Knowledge** – Track updates, context changes, and lineage.\
✅ **Graph Relationships** – Understand how data evolves and influences actions.\
✅ **Semantic Search** – Retrieve insights with **pgvector-powered** similarity matching.\
✅ **GraphQL API + SDK** – Query structured memory seamlessly with **Hasura**.\
✅ **Operational Workflows** – Lay the foundation for **fully autonomous business ventures**.\
✅ **Fully Open-Source & Portable** – No vendor lock-in, self-host on any PostgreSQL-compatible infrastructure.

## 🔥 Getting Started

### Install & Create a New Instance

```bash
pip install mesh-os
mesh-os create my-project && cd my-project
mesh-os up
```

### Register an AI Agent

```bash
mesh-os agent register "strategic-analyst"
```

### Store a Memory

```bash
mesh-os memory remember "The company should expand into renewable energy..."
```

### Retrieve Knowledge via Semantic Search

```bash
mesh-os memory recall "What business strategies are stored?"
```

### Link Related Memories

```bash
mesh-os memory link <memory-id-1> <memory-id-2> --relationship "influences"
```

## 📚 Python SDK Example

```python
from mesh_os import MeshOS

# Initialize MeshOS
os = MeshOS()

# Register an agent
agent = os.register_agent(name="strategic-analyst")

# Store structured knowledge
memory = os.remember(
    content="The company should expand into renewable energy...",
    agent_id=agent.id,
    metadata={
        "type": "decision",
        "subtype": "company-strategy",
        "tags": ["growth", "sustainability"],
        "version": 1
    }
)

# Retrieve similar knowledge
results = os.recall(query="What are the company's growth strategies?")
```

## 🔗 Structured Taxonomy & Memory Graph

MeshOS **enforces structured knowledge** with **memory classification** and **versioning**:

| **Memory Type** | **Examples**                                 |
| --------------- | -------------------------------------------- |
| **Knowledge**   | Research reports, datasets, company strategy |
| **Activity**    | Agent workflows, logs, system events         |
| **Decision**    | Policy updates, business strategy            |
| **Media**       | Documents, images, AI-generated content      |

Memories **evolve** over time, with full versioning and relationship tracking.

## 🛠️ Full Documentation

### **Configuration**

The `.env` file supports the following options:

```ini
# Required
OPENAI_API_KEY=your_api_key_here

# Optional (defaults shown)
POSTGRES_PASSWORD=mysecretpassword
HASURA_ADMIN_SECRET=meshos
POSTGRES_PORT=5432
HASURA_PORT=8080
HASURA_ENABLE_CONSOLE=true
```

### **Development**

Clone the repository:

```bash
git clone https://github.com/Props-Labs/mesh-os.git
cd mesh-os
```

Install dependencies:

```bash
poetry install
```

Run tests:

```bash
poetry run pytest
```

### **Contributing**

Contributions are welcome! Please submit a Pull Request.

## ⚖️ License

MIT License – see [LICENSE](./LICENSE) for details.

