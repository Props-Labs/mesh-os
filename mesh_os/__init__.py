"""
MeshOS - A lightweight multi-agent memory system with semantic search.
"""

from mesh_os.core.client import Agent, Memory, MemoryEdge, MeshOS
from mesh_os.core.taxonomy import (ActivitySubtype, DataType, DecisionSubtype,
                                  EdgeMetadata, EdgeType, KnowledgeSubtype,
                                  MediaSubtype, MemoryMetadata, RelevanceTag,
                                  VersionInfo)

__version__ = "0.1.0"
__all__ = [
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