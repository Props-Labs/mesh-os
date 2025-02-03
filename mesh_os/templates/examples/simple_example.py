"""
Simple example demonstrating MeshOS usage.
"""
import os
from dotenv import load_dotenv

from mesh_os.core.client import MeshOS

# Load environment variables
load_dotenv()

def main():
    """Run the example."""
    # Initialize client
    client = MeshOS(
        url=os.getenv("HASURA_URL", "http://localhost:8080"),
        api_key=os.getenv("HASURA_ADMIN_SECRET", "meshos")
    )
    
    try:
        # Create an agent
        print("Creating agent...")
        agent = client.create_agent(
            id="test-agent",
            name="TestAgent",
            description="A test agent",
            metadata={"role": "example"}
        )
        print(f"Created agent: {agent.id}")
        
        # Store some memories
        print("\nStoring memories...")
        memories = [
            "The quick brown fox jumps over the lazy dog.",
            "Python is a versatile programming language.",
            "Machine learning models can understand text semantics."
        ]
        
        for text in memories:
            memory = client.remember(text, agent_id=agent.id)
            print(f"Stored memory: {memory.id}")
        
        # Search for similar memories
        print("\nSearching memories...")
        query = "Tell me about programming languages"
        results = client.recall(query, agent_id=agent.id, limit=2)
        
        print(f"Found {len(results)} relevant memories:")
        for i, memory in enumerate(results, 1):
            print(f"\n{i}. Memory {memory.id}")
            print(f"Content: {memory.content}")
        
        # Clean up
        print("\nCleaning up...")
        client.delete_agent(agent.id)
        print("Agent and memories deleted")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 