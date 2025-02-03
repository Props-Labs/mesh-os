"""
Core functionality for MeshOS.
"""
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Union

import openai
import requests
from rich.console import Console
from rich.panel import Panel

from mesh_os.core.taxonomy import (DataType, EdgeMetadata, EdgeType, MemoryMetadata,
                                  RelevanceTag, VersionInfo, KnowledgeSubtype)

console = Console()

@dataclass
class Agent:
    """An agent in the system."""
    id: str
    name: str
    description: str
    metadata: Dict
    status: str

@dataclass
class Memory:
    """A memory stored in the system."""
    id: str
    agent_id: str
    content: str
    metadata: MemoryMetadata
    embedding: List[float]
    created_at: str
    updated_at: str

@dataclass
class MemoryEdge:
    """A connection between two memories."""
    id: str
    source_memory: str
    target_memory: str
    relationship: EdgeType
    weight: float
    created_at: str
    metadata: EdgeMetadata

class GraphQLError(Exception):
    """Raised when a GraphQL query fails."""
    pass

class MeshOS:
    """MeshOS client for interacting with the system."""
    
    def __init__(
        self,
        url: str = "http://localhost:8080",
        api_key: str = "meshos",
        openai_api_key: Optional[str] = None
    ):
        """Initialize the MeshOS client."""
        self.url = f"{url}/v1/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "x-hasura-admin-secret": api_key
        }
        
        # Set up OpenAI
        openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            console.print(Panel(
                "[yellow]⚠️  OpenAI API key not found![/]\n\n"
                "Please set your OpenAI API key in the environment:\n"
                "[green]OPENAI_API_KEY=your-key-here[/]\n\n"
                "You can get an API key at: [blue]https://platform.openai.com/api-keys[/]",
                title="Missing API Key",
                border_style="yellow"
            ))
            raise ValueError("OpenAI API key is required")
        
        self.openai = openai.OpenAI(api_key=openai_api_key)
    
    def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query."""
        response = requests.post(
            self.url,
            headers=self.headers,
            json={
                "query": query,
                "variables": variables or {}
            }
        )
        response.raise_for_status()
        result = response.json()
        
        if "errors" in result:
            error_msg = result["errors"][0]["message"]
            raise GraphQLError(error_msg)
        
        return result
    
    def _create_embedding(self, text: str) -> List[float]:
        """Create an embedding for the given text."""
        response = self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    def register_agent(
        self,
        name: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> Agent:
        """Register a new agent in the system."""
        query = """
        mutation RegisterAgent($name: String!, $description: String!, $metadata: jsonb) {
          insert_agents_one(object: {
            name: $name,
            description: $description,
            metadata: $metadata,
            status: "active"
          }) {
            id
            name
            description
            metadata
            status
          }
        }
        """
        result = self._execute_query(query, {
            "name": name,
            "description": description,
            "metadata": metadata or {}
        })
        agent_data = result["data"]["insert_agents_one"]
        return Agent(**agent_data)
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent and remove all their memories."""
        query = """
        mutation UnregisterAgent($id: uuid!) {
          delete_agents_by_pk(id: $id) {
            id
          }
        }
        """
        result = self._execute_query(query, {"id": agent_id})
        return bool(result["data"]["delete_agents_by_pk"])
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent details by ID."""
        query = """
        query GetAgent($id: uuid!) {
          agents_by_pk(id: $id) {
            id
            name
            description
            metadata
            status
          }
        }
        """
        result = self._execute_query(query, {"id": agent_id})
        agent_data = result["data"]["agents_by_pk"]
        return Agent(**agent_data) if agent_data else None
    
    def remember(
        self,
        content: str,
        agent_id: str,
        metadata: Optional[Union[Dict, MemoryMetadata]] = None
    ) -> Memory:
        """Store a new memory."""
        # Convert dict to MemoryMetadata if needed
        if isinstance(metadata, dict):
            metadata = MemoryMetadata(**metadata)
        elif metadata is None:
            metadata = MemoryMetadata(
                type=DataType.KNOWLEDGE,
                subtype=KnowledgeSubtype.DATASET,
                tags=[],
                version=1
            )
        
        # Create embedding
        embedding = self._create_embedding(content)
        
        # Convert embedding to string format that Hasura expects for vector type
        embedding_str = f"[{','.join(str(x) for x in embedding)}]"
        
        # Convert metadata to dict for storage
        metadata_dict = metadata.model_dump()
        
        query = """
        mutation Remember($content: String!, $agent_id: uuid!, $metadata: jsonb, $embedding: vector!) {
          insert_memories_one(object: {
            content: $content,
            agent_id: $agent_id,
            metadata: $metadata,
            embedding: $embedding
          }) {
            id
            agent_id
            content
            metadata
            embedding
            created_at
            updated_at
          }
        }
        """
        result = self._execute_query(query, {
            "content": content,
            "agent_id": agent_id,
            "metadata": metadata_dict,
            "embedding": embedding_str
        })
        memory_data = result["data"]["insert_memories_one"]
        
        # Convert stored metadata back to MemoryMetadata if it's a dict
        if isinstance(memory_data["metadata"], dict):
            memory_data["metadata"] = MemoryMetadata(**memory_data["metadata"])
        
        return Memory(**memory_data)
    
    def recall(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.7,
        filters: Optional[Dict] = None
    ) -> List[Memory]:
        """Search memories by semantic similarity."""
        # Create embedding for the query
        embedding_str = f"[{','.join(str(x) for x in self._create_embedding(query))}]"
        
        # Construct the query
        query = """
        query SearchMemories(
            $query_embedding: vector!,
            $match_threshold: float8!,
            $match_count: Int!,
            $agent_id: uuid
        ) {
            search_memories(
                query_embedding: $query_embedding,
                match_threshold: $match_threshold,
                match_count: $match_count,
                filter_agent_id: $agent_id
            ) {
                id
                agent_id
                content
                metadata
                embedding
                similarity
                created_at
                updated_at
            }
        }
        """
        
        # Execute the query
        result = self._execute_query(query, {
            "query_embedding": embedding_str,
            "match_threshold": threshold,
            "match_count": limit,
            "agent_id": agent_id
        })
        
        # Convert results to Memory objects
        memories = []
        for m in result["data"]["search_memories"]:
            # Remove similarity from the dict before creating Memory object
            similarity = m.pop("similarity", None)
            memories.append(Memory(**m))
        
        return memories
    
    def forget(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        query = """
        mutation Forget($id: uuid!) {
          delete_memories_by_pk(id: $id) {
            id
          }
        }
        """
        result = self._execute_query(query, {"id": memory_id})
        return bool(result["data"]["delete_memories_by_pk"])

    def link_memories(
        self,
        source_memory_id: str,
        target_memory_id: str,
        relationship: Union[str, EdgeType],
        weight: float = 1.0,
        metadata: Optional[Union[Dict, EdgeMetadata]] = None
    ) -> MemoryEdge:
        """Create a link between two memories."""
        # Convert string to EdgeType if needed
        if isinstance(relationship, str):
            relationship = EdgeType(relationship)
        
        # Create edge metadata
        if isinstance(metadata, dict):
            metadata = EdgeMetadata(relationship=relationship, weight=weight, **metadata)
        elif metadata is None:
            metadata = EdgeMetadata(relationship=relationship, weight=weight)
        
        query = """
        mutation LinkMemories(
            $source_memory: uuid!,
            $target_memory: uuid!,
            $relationship: String!,
            $weight: float8!,
            $metadata: jsonb!
        ) {
            insert_memory_edges_one(object: {
                source_memory: $source_memory,
                target_memory: $target_memory,
                relationship: $relationship,
                weight: $weight,
                metadata: $metadata
            }) {
                id
                source_memory
                target_memory
                relationship
                weight
                created_at
                metadata
            }
        }
        """
        result = self._execute_query(query, {
            "source_memory": source_memory_id,
            "target_memory": target_memory_id,
            "relationship": relationship.value,
            "weight": weight,
            "metadata": metadata.model_dump()
        })
        edge_data = result["data"]["insert_memory_edges_one"]
        
        # Convert stored metadata back to EdgeMetadata if it's a dict
        if isinstance(edge_data["metadata"], dict):
            edge_data["metadata"] = EdgeMetadata(**edge_data["metadata"])
        
        # Convert relationship string to EdgeType
        edge_data["relationship"] = EdgeType(edge_data["relationship"])
        
        return MemoryEdge(**edge_data)

    def unlink_memories(
        self,
        source_memory_id: str,
        target_memory_id: str,
        relationship: Optional[str] = None
    ) -> bool:
        """Remove links between two memories."""
        conditions = {
            "source_memory": {"_eq": source_memory_id},
            "target_memory": {"_eq": target_memory_id}
        }
        if relationship:
            conditions["relationship"] = {"_eq": relationship}
        
        query = """
        mutation UnlinkMemories($where: memory_edges_bool_exp!) {
            delete_memory_edges(where: $where) {
                affected_rows
            }
        }
        """
        result = self._execute_query(query, {
            "where": conditions
        })
        return result["data"]["delete_memory_edges"]["affected_rows"] > 0

    def update_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Union[Dict, MemoryMetadata]] = None,
        create_version_edge: bool = True
    ) -> Memory:
        """Update a memory and optionally create a version edge to the previous version."""
        # First get the current memory
        query = """
        query GetMemory($id: uuid!) {
            memories_by_pk(id: $id) {
                id
                agent_id
                content
                metadata
                embedding
                created_at
                updated_at
            }
        }
        """
        result = self._execute_query(query, {"id": memory_id})
        old_memory = result["data"]["memories_by_pk"]
        if not old_memory:
            raise ValueError(f"Memory {memory_id} not found")
        
        # Convert old metadata to MemoryMetadata if it's a dict
        old_metadata = old_memory["metadata"]
        if isinstance(old_metadata, dict):
            old_metadata = MemoryMetadata(**old_metadata)
        
        # Prepare new metadata
        if isinstance(metadata, dict):
            metadata = MemoryMetadata(**metadata)
        elif metadata is None:
            metadata = MemoryMetadata(**old_metadata.model_dump())
        
        # Update version information
        metadata.version = old_metadata.version + 1
        metadata.previous_version = old_memory["id"]
        metadata.history.append(VersionInfo(
            version=old_metadata.version,
            modified_at=datetime.fromisoformat(old_memory["updated_at"].replace("Z", "+00:00")),
            modified_by=old_memory["agent_id"]
        ))
        
        # Create new memory
        new_memory = self.remember(
            content=content,
            agent_id=old_memory["agent_id"],
            metadata=metadata
        )
        
        # Create version edge if requested
        if create_version_edge:
            self.link_memories(
                source_memory_id=old_memory["id"],
                target_memory_id=new_memory.id,
                relationship=EdgeType.VERSION_OF,
                weight=1.0,
                metadata=EdgeMetadata(
                    relationship=EdgeType.VERSION_OF,
                    weight=1.0,
                    bidirectional=False,
                    additional={"version_increment": 1}
                )
            )
        
        return new_memory

    def get_connected_memories(
        self,
        memory_id: str,
        relationship: Optional[str] = None,
        max_depth: int = 1
    ) -> List[Dict]:
        """Get memories connected to the given memory."""
        query = """
        query GetConnectedMemories(
            $memory_id: uuid!,
            $relationship: String,
            $max_depth: Int!
        ) {
            get_connected_memories(
                memory_id: $memory_id,
                relationship_type: $relationship,
                max_depth: $max_depth
            ) {
                source_id
                target_id
                relationship
                weight
                depth
            }
        }
        """
        result = self._execute_query(query, {
            "memory_id": memory_id,
            "relationship": relationship,
            "max_depth": max_depth
        })
        return result["data"]["get_connected_memories"] 