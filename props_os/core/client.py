"""
PropsOS Client - A simple interface for the PropsOS memory system.
"""
from typing import Dict, List, Optional
import json
import os

import openai
import requests
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel

console = Console()

class Memory(BaseModel):
    """Memory model representing a stored memory."""
    id: str
    agent_id: Optional[str]
    content: str
    metadata: Optional[Dict] = None
    embedding: Optional[List[float]] = None

class Agent(BaseModel):
    """Agent model representing a registered agent."""
    id: str
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict] = None
    status: str = "active"

class PropsOS:
    """
    PropsOS Client - Simple interface for storing and retrieving memories.
    
    Example:
        client = PropsOS(url="http://localhost:8080", api_key="your-key")
        
        # Store a memory
        memory = client.remember("This is a memory", agent_id="agent-1")
        
        # Find similar memories
        memories = client.recall("What was that memory about?", limit=5)
    """
    
    def __init__(
        self,
        url: str = "http://localhost:8080",
        api_key: str = "myhasurasecret",
        openai_api_key: Optional[str] = None
    ):
        """Initialize the PropsOS client."""
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
        
        openai.api_key = openai_api_key
    
    def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query."""
        response = requests.post(
            self.url,
            json={"query": query, "variables": variables or {}},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI's API."""
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            encoding_format="float"
        )
        return response.data[0].embedding
    
    def remember(
        self,
        content: str,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Memory:
        """
        Store a new memory.
        
        Args:
            content: The text content to remember
            agent_id: Optional ID of the agent this memory belongs to
            metadata: Optional metadata about the memory
            
        Returns:
            Memory object containing the stored memory details
        """
        try:
            embedding = self._get_embedding(content)
        except Exception as e:
            console.print(Panel(
                f"[red]Error generating embedding: {str(e)}[/]\n\n"
                "Please check your OpenAI API key and try again.",
                title="Embedding Error",
                border_style="red"
            ))
            raise
        
        mutation = """
        mutation AddMemory(
          $agent_id: uuid,
          $content: String!,
          $metadata: jsonb,
          $embedding: _float8!
        ) {
          insert_memories_one(object: {
            agent_id: $agent_id,
            content: $content,
            metadata: $metadata,
            embedding: $embedding
          }) {
            id
            agent_id
            content
            metadata
            embedding
          }
        }
        """
        variables = {
            "agent_id": agent_id,
            "content": content,
            "metadata": metadata,
            "embedding": embedding
        }
        result = self._execute_query(mutation, variables)
        return Memory(**result["data"]["insert_memories_one"])
    
    def recall(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.7
    ) -> List[Memory]:
        """
        Find similar memories using semantic search.
        
        Args:
            query: The text to search for
            agent_id: Optional agent ID to filter memories
            limit: Maximum number of memories to return
            threshold: Minimum similarity threshold (0-1)
            
        Returns:
            List of Memory objects sorted by relevance
        """
        try:
            query_embedding = self._get_embedding(query)
        except Exception as e:
            console.print(Panel(
                f"[red]Error generating embedding: {str(e)}[/]\n\n"
                "Please check your OpenAI API key and try again.",
                title="Embedding Error",
                border_style="red"
            ))
            raise
        
        query = """
        query SearchMemories(
          $embedding: _float8!,
          $limit: Int!,
          $agent_id: uuid
        ) {
          search_memories(
            args: {
              query_vector: $embedding,
              similarity_threshold: $threshold,
              max_results: $limit
            },
            where: { agent_id: { _eq: $agent_id } }
          ) {
            id
            agent_id
            content
            metadata
            embedding
          }
        }
        """
        variables = {
            "embedding": query_embedding,
            "limit": limit,
            "agent_id": agent_id
        }
        result = self._execute_query(query, variables)
        return [Memory(**m) for m in result["data"]["search_memories"]]
    
    def forget(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        mutation = """
        mutation DeleteMemory($id: uuid!) {
          delete_memories_by_pk(id: $id) {
            id
          }
        }
        """
        result = self._execute_query(mutation, {"id": memory_id})
        return result["data"]["delete_memories_by_pk"] is not None
    
    def create_agent(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Agent:
        """Create a new agent."""
        mutation = """
        mutation CreateAgent(
          $name: String!,
          $description: String,
          $metadata: jsonb
        ) {
          insert_agents_one(object: {
            name: $name,
            description: $description,
            metadata: $metadata
          }) {
            id
            name
            description
            metadata
            status
          }
        }
        """
        variables = {
            "name": name,
            "description": description,
            "metadata": metadata
        }
        result = self._execute_query(mutation, variables)
        return Agent(**result["data"]["insert_agents_one"])
    
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
    
    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent and all their memories."""
        mutation = """
        mutation DeleteAgent($id: uuid!) {
          delete_agents_by_pk(id: $id) {
            id
          }
        }
        """
        result = self._execute_query(mutation, {"id": agent_id})
        return result["data"]["delete_agents_by_pk"] is not None 