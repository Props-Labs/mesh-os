"""
Taxonomy and classification models for MeshOS.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

class DataType(str, Enum):
    """Primary data type classification."""
    ACTIVITY = "activity"  # Agent & system actions
    KNOWLEDGE = "knowledge"  # Structured information
    DECISION = "decision"  # Strategic & operational choices
    MEDIA = "media"  # Files & content

class ActivitySubtype(str, Enum):
    """Subtypes for activity data."""
    AGENT_CONVERSATION = "agent-conversation"  # Structured record of agent interactions
    AGENT_LOG = "agent-log"  # System-level agent actions
    EXECUTION_LOG = "execution-log"  # Action execution records
    EVENT_LOG = "event-log"  # System events and notifications
    WORKFLOW_STEP = "workflow-step"  # Steps in multi-step processes

class KnowledgeSubtype(str, Enum):
    """Subtypes for knowledge data."""
    COMPANY_METADATA = "company-metadata"  # Core company information
    COMPANY_MISSION = "company-mission"  # Company's core purpose
    COMPANY_VISION = "company-vision"  # Strategic direction
    AGENT_MISSION = "agent-mission"  # Agent's specific role
    AGENT_VISION = "agent-vision"  # Agent's long-term goals
    RESEARCH_REPORT = "research-report"  # Analysis and findings
    FAQ_ENTRY = "faq-entry"  # Common QA entries
    DATASET = "dataset"  # Structured data collections
    OKRS = "okrs"  # Objectives and Key Results

class DecisionSubtype(str, Enum):
    """Subtypes for decision data."""
    POLICY_UPDATE = "policy-update"  # Policy changes
    COMPANY_STRATEGY = "company-strategy"  # Strategic initiatives
    SYSTEM_DECISION = "system-decision"  # System-level choices
    USER_FEEDBACK_DECISION = "user-feedback-decision"  # User input based decisions

class MediaSubtype(str, Enum):
    """Subtypes for media data."""
    IMAGE = "image"  # Image files
    VIDEO = "video"  # Video content
    TEXT_DOCUMENT = "text-document"  # Text-based documents
    GENERATED_CONTENT = "generated-content"  # AI-generated content

class EdgeType(str, Enum):
    """Standard relationship types for memory edges."""
    RELATED_TO = "related_to"  # Generic association
    VERSION_OF = "version_of"  # Updated version
    FOLLOWS_UP = "follows_up"  # Sequential relationship
    CONTRADICTS = "contradicts"  # Conflicting information
    DEPENDS_ON = "depends_on"  # Prerequisite relationship
    SUMMARIZES = "summarizes"  # Condensed version
    INFLUENCES = "influences"  # Impact relationship

class RelevanceTag(str, Enum):
    """Relevance classification tags."""
    HIGH_RELEVANCE = "high-relevance"
    TIME_SENSITIVE = "time-sensitive"
    ARCHIVAL = "archival"
    VOLATILE = "volatile"
    EXPERIMENTAL = "experimental"

class VersionInfo(BaseModel):
    """Version history entry."""
    version: int
    modified_at: datetime
    modified_by: str

class MemoryMetadata(BaseModel):
    """
    Standardized metadata structure for memories.
    
    This model enforces the taxonomy and classification guidelines
    for all memories stored in MeshOS.
    
    Examples:
        # Log an agent conversation
        metadata = MemoryMetadata(
            type=DataType.ACTIVITY,
            subtype=ActivitySubtype.AGENT_CONVERSATION,
            tags=["customer-service", "inquiry"],
            additional={
                "participants": ["agent-123", "user-456"],
                "conversation_id": "conv-789",
                "sentiment": "positive"
            }
        )
        
        # Store execution logs
        metadata = MemoryMetadata(
            type=DataType.ACTIVITY,
            subtype=ActivitySubtype.EXECUTION_LOG,
            tags=["api-call", "external-service"],
            relevance=RelevanceTag.VOLATILE,
            additional={
                "service": "openai",
                "endpoint": "/v1/embeddings",
                "status_code": 200,
                "latency_ms": 150
            }
        )
    """
    type: DataType = Field(..., description="Primary classification of the memory")
    subtype: str = Field(..., description="Secondary classification specific to the type")
    tags: List[str] = Field(default_factory=list, description="Custom tags for flexible categorization")
    relevance: Optional[RelevanceTag] = Field(None, description="Relevance classification")
    valid_until: Optional[datetime] = Field(None, description="Expiry timestamp for the memory")
    version: int = Field(default=1, description="Current version number")
    history: List[VersionInfo] = Field(default_factory=list, description="Version history")
    previous_version: Optional[str] = Field(None, description="UUID of the previous version")
    
    # Additional metadata fields can be added by users
    additional: Dict = Field(default_factory=dict, description="Custom metadata fields")

    @validator('subtype')
    def validate_subtype(cls, v, values):
        """Validate subtype based on the primary type."""
        type_subtypes = {
            DataType.ACTIVITY: [st.value for st in ActivitySubtype],
            DataType.KNOWLEDGE: [st.value for st in KnowledgeSubtype],
            DataType.DECISION: [st.value for st in DecisionSubtype],
            DataType.MEDIA: [st.value for st in MediaSubtype]
        }
        
        if 'type' in values and v not in type_subtypes.get(values['type'], []):
            valid_subtypes = type_subtypes.get(values['type'], [])
            raise ValueError(
                f"Invalid subtype '{v}' for type '{values['type']}'. "
                f"Valid subtypes are: {', '.join(valid_subtypes)}"
            )
        return v

    @validator('tags')
    def validate_tags(cls, v):
        """Ensure tags follow naming conventions."""
        for tag in v:
            if not tag.islower() or ' ' in tag:
                raise ValueError(
                    f"Invalid tag format: '{tag}'. Tags must be lowercase "
                    "and use hyphens instead of spaces."
                )
        return v

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "type": "activity",
                "subtype": "agent-conversation",
                "tags": ["customer-service", "inquiry"],
                "relevance": "high-relevance",
                "valid_until": "2025-01-01T00:00:00Z",
                "version": 1,
                "history": [],
                "additional": {
                    "participants": ["agent-123", "user-456"],
                    "conversation_id": "conv-789",
                    "sentiment": "positive"
                }
            }
        }

class EdgeMetadata(BaseModel):
    """
    Metadata structure for memory edges.
    
    This model standardizes how relationships between memories
    are classified and weighted.
    """
    relationship: EdgeType = Field(..., description="Type of relationship between memories")
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Strength of the relationship (0.0 to 1.0)"
    )
    valid_until: Optional[datetime] = Field(None, description="Expiry timestamp for the relationship")
    bidirectional: bool = Field(
        default=False,
        description="Whether the relationship applies in both directions"
    )
    additional: Dict = Field(default_factory=dict, description="Custom edge metadata")

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "relationship": "related_to",
                "weight": 0.8,
                "bidirectional": True,
                "additional": {
                    "context": "same-research-project",
                    "established_by": "agent-123"
                }
            }
        } 