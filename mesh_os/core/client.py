"""
Core functionality for MeshOS.
"""
import json
import os
import re
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

class InvalidSlugError(Exception):
    """Raised when an invalid slug is provided."""
    pass

@dataclass
class Agent:
    """An agent in the system."""
    id: str
    name: str
    description: str
    metadata: Dict
    status: str
    slug: Optional[str] = None

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
    expires_at: Optional[str] = None
    similarity: Optional[float] = None  # Add similarity field

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
    
    SLUG_PATTERN = re.compile(r'^[a-z][a-z0-9_-]*[a-z0-9]$')
    
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
    
    def _validate_slug(self, slug: str) -> bool:
        """Validate a slug string."""
        return bool(self.SLUG_PATTERN.match(slug))
    
    def _chunk_content(self, content: str, max_tokens: int = 8192) -> List[str]:
        """Split content into chunks that fit within token limit.
        
        Args:
            content: The text content to chunk
            max_tokens: Maximum tokens per chunk (default: 8192 for OpenAI embeddings)
            
        Returns:
            List of content chunks
        """
        # Use OpenAI's tokenizer to count tokens
        encoding = self.openai.tiktoken.encoding_for_model("text-embedding-3-small")
        tokens = encoding.encode(content)
        
        if len(tokens) <= max_tokens:
            return [content]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Split on sentence boundaries when possible
        sentences = content.split(". ")
        
        for sentence in sentences:
            # Add period back if it was removed by split
            sentence = sentence + "." if sentence == sentences[-1] else sentence + ". "
            sentence_tokens = encoding.encode(sentence)
            
            if current_length + len(sentence_tokens) > max_tokens:
                # Current chunk is full, start a new one
                if current_chunk:
                    chunks.append("".join(current_chunk))
                current_chunk = [sentence]
                current_length = len(sentence_tokens)
            else:
                current_chunk.append(sentence)
                current_length += len(sentence_tokens)
        
        # Add the last chunk if there is one
        if current_chunk:
            chunks.append("".join(current_chunk))
        
        return chunks

    def register_agent(
        self,
        name: str,
        description: str,
        metadata: Optional[Dict] = None,
        slug: Optional[str] = None
    ) -> Agent:
        """Register a new agent in the system.
        
        Args:
            name: The agent's display name
            description: A description of the agent
            metadata: Optional metadata dictionary
            slug: Optional unique slug for the agent (must be lowercase with hyphens/underscores)
            
        Returns:
            Agent: The registered agent
            
        Raises:
            InvalidSlugError: If the provided slug is invalid
            GraphQLError: If an agent with the slug already exists
        """
        if slug is not None and not self._validate_slug(slug):
            raise InvalidSlugError(
                "Slug must start with a letter and contain only lowercase letters, "
                "numbers, hyphens, and underscores"
            )
        
        # First check if agent with slug exists
        if slug:
            existing = self.get_agent_by_slug(slug)
            if existing:
                return existing
        
        query = """
        mutation RegisterAgent($name: String!, $description: String!, $metadata: jsonb, $slug: String) {
          insert_agents_one(object: {
            name: $name,
            description: $description,
            metadata: $metadata,
            status: "active",
            slug: $slug
          }) {
            id
            name
            description
            metadata
            status
            slug
          }
        }
        """
        result = self._execute_query(query, {
            "name": name,
            "description": description,
            "metadata": metadata or {},
            "slug": slug
        })
        agent_data = result["data"]["insert_agents_one"]
        return Agent(**agent_data)
    
    def get_agent_by_slug(self, slug: str) -> Optional[Agent]:
        """Get agent details by slug."""
        if not self._validate_slug(slug):
            raise InvalidSlugError(
                "Slug must start with a letter and contain only lowercase letters, "
                "numbers, hyphens, and underscores"
            )
        
        query = """
        query GetAgentBySlug($slug: String!) {
          agents(where: {slug: {_eq: $slug}}, limit: 1) {
            id
            name
            description
            metadata
            status
            slug
          }
        }
        """
        result = self._execute_query(query, {"slug": slug})
        agents = result["data"]["agents"]
        return Agent(**agents[0]) if agents else None

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
            slug
          }
        }
        """
        result = self._execute_query(query, {"id": agent_id})
        agent_data = result["data"]["agents_by_pk"]
        return Agent(**agent_data) if agent_data else None

    def update_agent_status(self, agent_id: str, status: str) -> Agent:
        """Update an agent's status.
        
        Args:
            agent_id: The ID of the agent to update
            status: The new status to set (e.g., 'active', 'inactive', 'error')
            
        Returns:
            Agent: The updated agent
            
        Raises:
            GraphQLError: If the agent doesn't exist or the update fails
        """
        query = """
        mutation UpdateAgentStatus($id: uuid!, $status: String!) {
          update_agents_by_pk(
            pk_columns: {id: $id}, 
            _set: {status: $status}
          ) {
            id
            name
            description
            metadata
            status
            slug
          }
        }
        """
        result = self._execute_query(query, {
            "id": agent_id,
            "status": status
        })
        agent_data = result["data"]["update_agents_by_pk"]
        return Agent(**agent_data)

    def remember(
        self,
        content: str,
        agent_id: str,
        metadata: Optional[Union[Dict, MemoryMetadata]] = None,
        expires_at: Optional[str] = None
    ) -> Union[Memory, List[Memory]]:
        """Store a new memory, automatically chunking if content exceeds token limit.
        
        Args:
            content: The text content to store
            agent_id: The ID of the agent creating the memory
            metadata: Optional metadata for the memory
            expires_at: Optional expiration timestamp in ISO 8601 format (e.g., "2025-02-05T00:00:00Z")
            
        Returns:
            Memory or List[Memory]: Single memory if content fits in one chunk,
            list of linked memories if content was chunked
            
        Examples:
            # Store a memory with expiration
            memory = mesh.remember(
                content="Important but temporary info",
                agent_id="agent-id",
                expires_at="2025-12-31T23:59:59Z"
            )
            
            # Store a memory with metadata and expiration
            memory = mesh.remember(
                content="Research findings",
                agent_id="agent-id",
                metadata={
                    "type": "knowledge",
                    "subtype": "research-report",
                    "tags": ["important"]
                },
                expires_at="2026-01-01T00:00:00Z"
            )
        """
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
        
        # Chunk the content if needed
        chunks = self._chunk_content(content)
        
        if len(chunks) == 1:
            # Single chunk case - proceed as before
            embedding = self._create_embedding(content)
            embedding_str = f"[{','.join(str(x) for x in embedding)}]"
            metadata_dict = metadata.model_dump()
            
            query = """
            mutation Remember($content: String!, $agent_id: uuid!, $metadata: jsonb, $embedding: vector!, $expires_at: timestamptz) {
              insert_memories_one(object: {
                content: $content,
                agent_id: $agent_id,
                metadata: $metadata,
                embedding: $embedding,
                expires_at: $expires_at
              }) {
                id
                agent_id
                content
                metadata
                embedding
                created_at
                updated_at
                expires_at
              }
            }
            """
            result = self._execute_query(query, {
                "content": content,
                "agent_id": agent_id,
                "metadata": metadata_dict,
                "embedding": embedding_str,
                "expires_at": expires_at
            })
            memory_data = result["data"]["insert_memories_one"]
            
            # Convert stored metadata back to MemoryMetadata if it's a dict
            if isinstance(memory_data["metadata"], dict):
                memory_data["metadata"] = MemoryMetadata(**memory_data["metadata"])
            
            return Memory(**memory_data)
        else:
            # Multiple chunks case
            memories = []
            previous_memory = None
            
            for i, chunk in enumerate(chunks):
                # Update metadata for chunk
                chunk_metadata = metadata.model_dump()
                chunk_metadata.update({
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "is_chunk": True
                })
                if previous_memory:
                    chunk_metadata["previous_chunk"] = previous_memory.id
                
                # Create embedding for chunk
                embedding = self._create_embedding(chunk)
                embedding_str = f"[{','.join(str(x) for x in embedding)}]"
                
                # Store chunk
                query = """
                mutation Remember($content: String!, $agent_id: uuid!, $metadata: jsonb, $embedding: vector!, $expires_at: timestamptz) {
                  insert_memories_one(object: {
                    content: $content,
                    agent_id: $agent_id,
                    metadata: $metadata,
                    embedding: $embedding,
                    expires_at: $expires_at
                  }) {
                    id
                    agent_id
                    content
                    metadata
                    embedding
                    created_at
                    updated_at
                    expires_at
                  }
                }
                """
                result = self._execute_query(query, {
                    "content": chunk,
                    "agent_id": agent_id,
                    "metadata": chunk_metadata,
                    "embedding": embedding_str,
                    "expires_at": expires_at
                })
                memory_data = result["data"]["insert_memories_one"]
                
                # Convert stored metadata back to MemoryMetadata
                if isinstance(memory_data["metadata"], dict):
                    memory_data["metadata"] = MemoryMetadata(**memory_data["metadata"])
                
                memory = Memory(**memory_data)
                memories.append(memory)
                
                # Link to previous chunk if it exists
                if previous_memory:
                    self.link_memories(
                        source_memory_id=memory.id,  # Current chunk points to the previous one
                        target_memory_id=previous_memory.id,
                        relationship=EdgeType.PART_OF,
                        weight=1.0,
                        metadata=EdgeMetadata(
                            relationship=EdgeType.PART_OF,
                            weight=1.0,
                            bidirectional=True,  # Both chunks are part of the same document
                            additional={
                                "document_sequence": True,
                                "sequence_index": i
                            }
                        )
                    )
                
                previous_memory = memory
            
            return memories

    def _expand_query(self, query: str, num_variations: int = 2) -> List[str]:
        """Generate semantic variations of the query.
        
        Args:
            query: The original query text
            num_variations: Number of variations to generate
            
        Returns:
            List of query variations including the original
        """
        system_prompt = f"""Generate {num_variations} semantic variations of the query that mean the same thing.
        Focus on different ways to express the same concept.
        Return ONLY the variations, one per line, no numbering or extra text.
        Variations should be concise and natural, similar in length to the original."""
        
        response = self.openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": system_prompt
            }, {
                "role": "user",
                "content": query
            }],
            temperature=0.7
        )
        
        result = [query]  # Include original
        result.extend([
            v.strip() for v in response.choices[0].message.content.split('\n')
            if v.strip()
        ])
        return result[:num_variations + 1]  # Limit to requested number of variations

    def recall(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.7,  # Strict default threshold
        min_results: int = 1,    # Start with finding just one good match
        adaptive_threshold: bool = True,
        use_semantic_expansion: bool = True,
        metadata_filter: Optional[Dict] = None,
        created_at_filter: Optional[Dict] = None,
        expires_at_filter: Optional[Dict] = None
    ) -> List[Memory]:
        """Search memories by semantic similarity.
        
        Args:
            query: The text to search for
            agent_id: Optional agent ID to filter by
            limit: Maximum number of results to return
            threshold: Initial similarity threshold (0-1, higher is more similar)
            min_results: Minimum number of results to return (default 1)
            adaptive_threshold: If True, gradually lower threshold until min_results is met
            use_semantic_expansion: If True, generate variations of the query when needed
            metadata_filter: Filter by metadata fields (e.g., {"type": "knowledge"})
            created_at_filter: Filter by creation time using operators (_gt, _gte, _lt, _lte, _eq)
            expires_at_filter: Filter by expiration time using operators (_gt, _gte, _lt, _lte, _eq)
            
        Returns:
            List of Memory objects with similarity scores, sorted by similarity
            
        Examples:
            # Search with creation time filter
            memories = mesh.recall(
                "query",
                created_at_filter={
                    "_gte": "2024-01-01T00:00:00Z",
                    "_lt": "2025-01-01T00:00:00Z"
                }
            )
            
            # Search with expiration and metadata filters
            memories = mesh.recall(
                "query",
                metadata_filter={"type": "knowledge"},
                expires_at_filter={"_gt": "2025-02-05T00:00:00Z"}
            )
        """
        # First try: Direct search with initial threshold
        results = self._recall_with_threshold(
            query=query,
            threshold=threshold,
            agent_id=agent_id,
            limit=limit,
            metadata_filter=metadata_filter,
            created_at_filter=created_at_filter,
            expires_at_filter=expires_at_filter
        )
        
        if len(results) >= min_results:
            return results[:limit]  # Found enough results, return immediately
        
        # Second try: If adaptive threshold is enabled, try lowering the threshold
        if adaptive_threshold:
            current_threshold = threshold - 0.05
            min_threshold = 0.3  # Don't go below this to avoid irrelevant matches
            
            while current_threshold >= min_threshold and len(results) < min_results:
                new_results = self._recall_with_threshold(
                    query=query,
                    threshold=current_threshold,
                    agent_id=agent_id,
                    limit=limit,
                    metadata_filter=metadata_filter,
                    created_at_filter=created_at_filter,
                    expires_at_filter=expires_at_filter
                )
                
                # Add new results that aren't already in the list
                for result in new_results:
                    if not any(r.id == result.id for r in results):
                        results.append(result)
                
                if len(results) >= min_results:
                    break
                    
                current_threshold -= 0.05
        
        # Third try: If we still don't have ANY results and semantic expansion is enabled
        if len(results) == 0 and use_semantic_expansion:  # Only expand if we found nothing
            variations = self._expand_query(query)
            seen_ids = {}  # Start fresh since we have no results
            
            # Try each variation with the original threshold first
            for variation in variations[1:]:  # Skip original query as we already tried it
                variation_results = self._recall_with_threshold(
                    query=variation,
                    threshold=threshold,
                    agent_id=agent_id,
                    limit=limit,
                    metadata_filter=metadata_filter,
                    created_at_filter=created_at_filter,
                    expires_at_filter=expires_at_filter
                )
                
                # Add new results or update if better similarity
                for memory in variation_results:
                    if memory.id not in seen_ids or (memory.similarity or 0) > (seen_ids[memory.id].similarity or 0):
                        seen_ids[memory.id] = memory
                
                if len(seen_ids) >= min_results:
                    break
            
            # If still no results, try variations with adaptive threshold
            if len(seen_ids) == 0 and adaptive_threshold:  # Only if we still have nothing
                current_threshold = threshold - 0.05
                
                while current_threshold >= min_threshold and len(seen_ids) == 0:  # Stop at first result
                    for variation in variations[1:]:
                        variation_results = self._recall_with_threshold(
                            query=variation,
                            threshold=current_threshold,
                            agent_id=agent_id,
                            limit=limit,
                            metadata_filter=metadata_filter,
                            created_at_filter=created_at_filter,
                            expires_at_filter=expires_at_filter
                        )
                        
                        for memory in variation_results:
                            if memory.id not in seen_ids or (memory.similarity or 0) > (seen_ids[memory.id].similarity or 0):
                                seen_ids[memory.id] = memory
                        
                        if len(seen_ids) > 0:  # Stop as soon as we find anything
                            break
                    
                    if len(seen_ids) > 0:
                        break
                    
                    current_threshold -= 0.05
                
                # Update results with any found memories
                if seen_ids:
                    results = list(seen_ids.values())
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x.similarity or 0, reverse=True)
        return results[:limit]

    def _recall_with_threshold(
        self,
        query: str,
        threshold: float,
        agent_id: Optional[str] = None,
        limit: int = 10,
        metadata_filter: Optional[Dict] = None,
        created_at_filter: Optional[Dict] = None,
        expires_at_filter: Optional[Dict] = None
    ) -> List[Memory]:
        """Internal method to perform recall with a specific threshold."""
        # Create embedding for the query
        embedding_str = f"[{','.join(str(x) for x in self._create_embedding(query))}]"
        
        # Construct the query
        query = """
        query SearchMemories(
            $args: search_memories_args!
        ) {
            search_memories(
                args: $args
            ) {
                id
                agent_id
                content
                metadata
                embedding
                similarity
                created_at
                updated_at
                expires_at
            }
        }
        """
        
        # Prepare the arguments
        args = {
            "query_embedding": embedding_str,
            "match_threshold": threshold,
            "match_count": limit,
            "filter_agent_id": agent_id
        }
        
        # Add filters if provided
        if metadata_filter:
            args["metadata_filter"] = metadata_filter
        if created_at_filter:
            args["created_at_filter"] = created_at_filter
        if expires_at_filter:
            args["expires_at_filter"] = expires_at_filter
        
        # Execute the query
        result = self._execute_query(query, {
            "args": args
        })
        
        # Convert results to Memory objects, preserving similarity scores
        memories = []
        for m in result["data"]["search_memories"]:
            similarity = m.pop("similarity", None)
            memory = Memory(**m)
            memory.similarity = similarity
            memories.append(memory)
        
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