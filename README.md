# MeshOS

**The Multi-Agent Framework for AI-Powered Operations**

MeshOS is an **opinionated framework** for building **multi-agent, multi-human AI-driven operations** with structured memory, intelligent workflows, and seamless collaboration. Unlike generic memory stores, MeshOS is purpose-built for:

- **Autonomous Agents & Teams** – Agents and humans share structured, evolving knowledge.
- **Graph-Based Memory** – Track relationships, dependencies, and influence between data points.
- **Rich Taxonomy & Classification** – Categorize knowledge, activities, decisions, and media.
- **Versioned Knowledge** – Full history, updates, and lineage tracking.
- **Event-Driven Operations** – Context-aware execution of decisions, workflows, and activities.
- **Open & Portable** – Built on **PostgreSQL**, **pgvector**, and **Hasura**, ensuring no vendor lock-in.

## 🚀 Why MeshOS?

Most frameworks give you a **blob of memories**—MeshOS gives you **structured, evolving intelligence.**

| Feature                      | MeshOS | Mem0 / Letta / Zep |
| ---------------------------- | ------ | ------------------ |
| **Multi-Agent Memory**       | ✅ Yes  | ❌ No               |
| **Structured Taxonomy**      | ✅ Yes  | ❌ No               |
| **Versioned Knowledge**      | ✅ Yes  | ❌ No               |
| **Graph-Based Relationships** | ✅ Yes  | ❌ No               |
| **Semantic & Vector Search**  | ✅ Yes  | ✅ Partial          |
| **Event-Driven Operations**  | ✅ Yes  | ❌ No               |
| **Open-Source & Portable**   | ✅ Yes  | ✅ Partial          |

### **Who is MeshOS for?**

✅ **Builders of AI-powered operations** – Structured memory and decision-making for AI-driven systems.  
✅ **Multi-agent system developers** – AI agents that need to store, process, and evolve shared knowledge.  
✅ **Developers & engineers** – Wanting an **open-source, PostgreSQL-powered framework** with no lock-in.  

---

## 🏗️ Core Features

✅ **AI-Driven Memory** – Store structured **knowledge, activities, decisions, and media**.  
✅ **Taxonomy & Classification** – Enforce hierarchical data models across agents.  
✅ **Multi-Agent Collaboration** – Agents operate independently, yet share structured memory.  
✅ **Graph-Based Memory** – Connect data intelligently with linked relationships.  
✅ **Versioned Knowledge** – Track updates, context changes, and lineage.  
✅ **Event-Driven Workflows** – Enable real-time, state-aware operations.  
✅ **Semantic Search** – Retrieve insights with **pgvector-powered** similarity matching.  
✅ **GraphQL API + SDK** – Query structured memory seamlessly with **Hasura**.  
✅ **Fully Open-Source & Portable** – Self-host on any PostgreSQL-compatible infrastructure.  

---

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

---

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

---

## 🔗 Structured Taxonomy & Memory Graph

MeshOS **enforces structured knowledge** with **memory classification** and **versioning**:

| **Memory Type** | **Examples**                                 |
| --------------- | -------------------------------------------- |
| **Knowledge**   | Research reports, datasets, company strategy |
| **Activity**    | Agent workflows, logs, system events         |
| **Decision**    | Policy updates, business strategy            |
| **Media**       | Documents, images, AI-generated content      |

Memories **evolve** over time, with full versioning and relationship tracking.

---

## 🛠️ Development & Configuration

### **Configuration**
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
```bash
git clone https://github.com/yourusername/mesh-os.git
cd mesh-os
poetry install
poetry run pytest
```

### **Contributing**
Contributions are welcome! Please submit a Pull Request.

---

## ⚖️ License
MIT License – see [LICENSE](./LICENSE) for details.

