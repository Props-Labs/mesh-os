"""
PropsOS - A lightweight multi-agent memory system with semantic search.
"""

from props_os.core.client import Agent, Memory, MemoryEdge, PropsOS
from props_os.core.taxonomy import (ActivitySubtype, DataType, DecisionSubtype,
                                  EdgeMetadata, EdgeType, KnowledgeSubtype,
                                  MediaSubtype, MemoryMetadata, RelevanceTag,
                                  VersionInfo)

__version__ = "0.1.0"
__all__ = [
    # Client classes
    "Agent",
    "Memory",
    "MemoryEdge",
    "PropsOS",
    
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