"""
Core functionality for PropsOS.
"""
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import openai
import requests
from rich.console import Console
from rich.panel import Panel

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
    metadata: Dict
    embedding: List[float]
    created_at: str
    updated_at: str

class GraphQLError(Exception):
    """Raised when a GraphQL query fails."""
    pass

class PropsOS:
    """PropsOS client for interacting with the system."""
    
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
        metadata: Optional[Dict] = None
    ) -> Memory:
        """Store a new memory."""
        embedding = self._create_embedding(content)
        
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
            "metadata": metadata or {},
            "embedding": embedding
        })
        memory_data = result["data"]["insert_memories_one"]
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
        embedding = self._create_embedding(query)
        
        # Build where clause
        where = {}
        if agent_id:
            where["agent_id"] = {"_eq": agent_id}
        if filters:
            for key, value in filters.items():
                if isinstance(value, dict):
                    where[key] = value
                else:
                    where[key] = {"_eq": value}
        
        query = """
        query SearchMemories($embedding: vector!, $where: memories_bool_exp, $limit: Int!) {
          search_memories(
            args: {
              query_embedding: $embedding,
              match_threshold: 0.7,
              match_count: $limit
            },
            where: $where
          ) {
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
            "embedding": embedding,
            "where": where,
            "limit": limit
        })
        return [Memory(**m) for m in result["data"]["search_memories"]]
    
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