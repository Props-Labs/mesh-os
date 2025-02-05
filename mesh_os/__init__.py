"""
MeshOS - A lightweight multi-agent memory system with semantic search.

This package provides a high-level interface for managing agent memories with semantic search capabilities.

Key Components:
    - MeshOS: Main client class for interacting with the memory system
    - Agent: Represents an agent in the system
    - Memory: Represents a stored memory with content and metadata
    - MemoryEdge: Represents a connection between two memories

Type System:
    - DataType: Primary classification of memories (ACTIVITY, KNOWLEDGE, etc.)
    - ActivitySubtype: Subtypes for activity data
    - KnowledgeSubtype: Subtypes for knowledge data
    - DecisionSubtype: Subtypes for decision data
    - MediaSubtype: Subtypes for media data
    - EdgeType: Types of relationships between memories
    - RelevanceTag: Relevance classification for memories

Example:
    >>> from mesh_os import MeshOS, DataType, KnowledgeSubtype
    >>> os = MeshOS()
    >>> agent = os.register_agent("AI_Explorer")
    >>> memory = os.remember(
    ...     content="The Moon has water ice.",
    ...     agent_id=agent.id,
    ...     metadata={
    ...         "type": DataType.KNOWLEDGE,
    ...         "subtype": KnowledgeSubtype.RESEARCH_REPORT,
    ...         "tags": ["astronomy", "moon"]
    ...     }
    ... )
"""

from typing import List, Dict, Optional, Union, Any

from mesh_os.core.client import Agent, Memory, MemoryEdge, MeshOS
from mesh_os.core.taxonomy import (
    ActivitySubtype,
    DataType,
    DecisionSubtype,
    EdgeMetadata,
    EdgeType,
    KnowledgeSubtype,
    MediaSubtype,
    MemoryMetadata,
    RelevanceTag,
    VersionInfo
)

__version__ = "0.1.9"

# Re-export core types with proper type hints
__all__: List[str] = [
    # Client classes
    "Agent",
    "Memory",
    "MemoryEdge",
    "MeshOS",
    
    # Taxonomy models
    "DataType",
    "ActivitySubtype",
    "KnowledgeSubtype",
    "DecisionSubtype",
    "MediaSubtype",
    "EdgeMetadata",
    "EdgeType",
    "MemoryMetadata",
    "RelevanceTag",
    "VersionInfo"
] 