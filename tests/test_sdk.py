"""
Tests for the MeshOS SDK.
"""
import json
from datetime import datetime, timezone
from typing import Dict, List
from unittest.mock import MagicMock, patch, call
import os as os_module  # Rename to avoid conflict

import pytest
from openai import OpenAI

from mesh_os import MeshOS
from mesh_os.core.client import Agent, GraphQLError, Memory, MemoryEdge
from mesh_os.core.taxonomy import DataType, EdgeType, MemoryMetadata, EdgeMetadata

# Test data
TEST_AGENT = {
    "id": "test-agent-id",
    "name": "TestAgent",
    "description": "Test description",
    "metadata": {"capabilities": ["test"]},
    "status": "active"
}

TEST_MEMORY = {
    "id": "test-memory-id",
    "agent_id": "test-agent-id",
    "content": "Test memory content",
    "metadata": {
        "type": "knowledge",
        "subtype": "dataset",
        "tags": ["test"],
        "version": 1
    },
    "embedding": [0.1] * 1536,  # Matches OpenAI's embedding size
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}

TEST_MEMORY_EDGE = {
    "id": "test-edge-id",
    "source_memory": "test-memory-id-1",
    "target_memory": "test-memory-id-2",
    "relationship": "related_to",
    "weight": 1.0,
    "created_at": "2024-01-01T00:00:00Z",
    "metadata": {
        "relationship": "related_to",
        "weight": 1.0,
        "bidirectional": False,
        "additional": {}
    }
}

@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables."""
    with patch.dict(os_module.environ, {"OPENAI_API_KEY": "test-key"}):
        yield

@pytest.fixture
def mock_openai():
    """Mock OpenAI's embedding creation and chat completion."""
    # Mock embeddings
    mock_embeddings = MagicMock()
    mock_embeddings.create.return_value = MagicMock(
        data=[
            MagicMock(
                embedding=[0.1] * 1536,
                index=0
            )
        ]
    )
    
    # Mock chat completions
    mock_chat = MagicMock()
    mock_chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="variation 1\nvariation 2"
                )
            )
        ]
    )
    
    mock_client = MagicMock()
    mock_client.embeddings = mock_embeddings
    mock_client.chat = mock_chat
    
    with patch("openai.OpenAI", return_value=mock_client):
        yield mock_client

@pytest.fixture
def mock_requests():
    """Mock all requests to Hasura."""
    with patch("requests.post") as mock:
        mock.return_value.status_code = 200
        yield mock

@pytest.fixture
def os(mock_openai, mock_requests):
    """Create a MeshOS instance with mocked dependencies."""
    return MeshOS(
        url="http://test-url",
        api_key="test-secret",
        openai_api_key="test-openai-key"
    )

def setup_mock_response(mock_requests, data):
    """Helper to set up mock response data."""
    mock_requests.return_value.json.return_value = {"data": data}
    return mock_requests

def verify_graphql_query(mock_requests, expected_operation):
    """Helper to verify GraphQL query structure."""
    request_data = mock_requests.call_args[1]["json"]
    assert "query" in request_data
    assert isinstance(request_data["query"], str)
    assert expected_operation in request_data["query"]

@pytest.fixture(autouse=True)
def reset_mocks(mock_openai, mock_requests):
    """Reset all mocks before each test."""
    mock_openai.reset_mock()
    mock_requests.reset_mock()
    yield

class TestAgentManagement:
    """Tests for agent-related operations."""
    
    def test_register_agent(self, os, mock_requests):
        """Test registering a new agent."""
        setup_mock_response(mock_requests, {
            "insert_agents_one": TEST_AGENT
        })
        
        agent = os.register_agent(
            name=TEST_AGENT["name"],
            description=TEST_AGENT["description"],
            metadata=TEST_AGENT["metadata"]
        )
        
        assert isinstance(agent, Agent)
        assert agent.id == TEST_AGENT["id"]
        assert agent.name == TEST_AGENT["name"]
        assert agent.metadata == TEST_AGENT["metadata"]
        
        # Verify GraphQL mutation
        verify_graphql_query(mock_requests, "mutation RegisterAgent")
    
    def test_unregister_agent(self, os, mock_requests):
        """Test unregistering an agent."""
        setup_mock_response(mock_requests, {
            "delete_agents_by_pk": {"id": TEST_AGENT["id"]}
        })
        
        result = os.unregister_agent(TEST_AGENT["id"])
        assert result is True
        
        # Verify GraphQL mutation
        verify_graphql_query(mock_requests, "mutation UnregisterAgent")
    
    def test_get_agent(self, os, mock_requests):
        """Test retrieving agent details."""
        setup_mock_response(mock_requests, {
            "agents_by_pk": TEST_AGENT
        })
        
        agent = os.get_agent(TEST_AGENT["id"])
        assert isinstance(agent, Agent)
        assert agent.id == TEST_AGENT["id"]
        
        # Verify GraphQL query
        verify_graphql_query(mock_requests, "query GetAgent")

class TestMemoryOperations:
    """Tests for memory-related operations."""
    
    def test_remember(self, os, mock_requests, mock_openai):
        """Test storing a new memory."""
        setup_mock_response(mock_requests, {
            "insert_memories_one": TEST_MEMORY
        })
        
        memory = os.remember(
            content=TEST_MEMORY["content"],
            agent_id=TEST_MEMORY["agent_id"],
            metadata=TEST_MEMORY["metadata"]
        )
        
        assert isinstance(memory, Memory)
        assert memory.id == TEST_MEMORY["id"]
        assert memory.content == TEST_MEMORY["content"]
        assert memory.metadata == TEST_MEMORY["metadata"]
        
        # Verify OpenAI embedding was requested
        mock_openai.embeddings.create.assert_called_once()
        
        # Verify GraphQL mutation
        verify_graphql_query(mock_requests, "mutation Remember")
    
    def test_recall_with_filters(self, os, mock_requests, mock_openai):
        """Test searching memories with filters."""
        # Mock a single response with similarity score
        response = {
            "data": {
                "search_memories": [
                    {**TEST_MEMORY, "similarity": 0.75}
                ]
            }
        }
        mock_requests.return_value.json.return_value = response
        
        filters = {
            "type": "test",
            "confidence": {"_gt": 0.8},
            "created_at": {"_gte": "2024-01-01"},
            "tags": {"_contains": ["important"]}
        }
        
        memories = os.recall(
            query="test query",
            agent_id=TEST_MEMORY["agent_id"],
            limit=5,
            threshold=0.7,
            filters=filters,
            use_semantic_expansion=False,  # Disable expansion for this test
            adaptive_threshold=False  # Disable adaptive threshold for this test
        )
        
        assert isinstance(memories, list)
        assert len(memories) == 1
        assert isinstance(memories[0], Memory)
        assert memories[0].id == TEST_MEMORY["id"]
        assert abs(memories[0].similarity - 0.75) < 1e-10
        
        # Verify OpenAI embedding was requested exactly once
        mock_openai.embeddings.create.assert_called_once()
        
        # Verify GraphQL query with filters
        verify_graphql_query(mock_requests, "query SearchMemories")
        variables = mock_requests.call_args[1]["json"]["variables"]
        assert "args" in variables

    def test_semantic_expansion(self, os, mock_requests, mock_openai):
        """Test query semantic expansion."""
        # Mock search results for different variations
        responses = [
            {
                "data": {
                    "search_memories": [
                        {**TEST_MEMORY, "id": "1", "similarity": 0.85},
                        {**TEST_MEMORY, "id": "2", "similarity": 0.75}
                    ]
                }
            },
            {
                "data": {
                    "search_memories": [
                        {**TEST_MEMORY, "id": "3", "similarity": 0.72},
                        {**TEST_MEMORY, "id": "4", "similarity": 0.70}
                    ]
                }
            },
            {
                "data": {
                    "search_memories": [
                        {**TEST_MEMORY, "id": "5", "similarity": 0.68},
                        {**TEST_MEMORY, "id": "6", "similarity": 0.65}
                    ]
                }
            }
        ]
        mock_requests.return_value.json.side_effect = responses * 3  # Ensure enough responses

        memories = os.recall(
            query="programming language",
            use_semantic_expansion=True,
            threshold=0.5,
            limit=4  # Explicitly set limit to 4
        )

        # Verify results are deduplicated and sorted
        assert len(memories) == 4  # Should get top 4 unique results
        assert [m.id for m in memories] == ["1", "2", "3", "4"]  # Top 4 by similarity
        assert abs(memories[0].similarity - 0.85) < 1e-10  # Highest similarity
        assert abs(memories[-1].similarity - 0.70) < 1e-10  # Lowest similarity of included results
        
        # Verify chat completion was called for expansion
        assert mock_openai.chat.completions.create.call_count == 1
        messages = mock_openai.chat.completions.create.call_args[1]["messages"]
        assert any("programming language" in msg["content"] for msg in messages)

    def test_adaptive_threshold(self, os, mock_requests, mock_openai):
        """Test adaptive threshold search."""
        # Mock a sequence of results with different thresholds
        mock_requests.return_value.json.side_effect = [
            # First try with threshold=0.7 (no results)
            {"data": {"search_memories": []}},
            # Second try with threshold=0.65 (no results)
            {"data": {"search_memories": []}},
            # Third try with threshold=0.6 (found results)
            {
                "data": {
                    "search_memories": [
                        {**TEST_MEMORY, "id": "1", "similarity": 0.62},
                        {**TEST_MEMORY, "id": "2", "similarity": 0.61},
                        {**TEST_MEMORY, "id": "3", "similarity": 0.60}
                    ]
                }
            }
        ] * 2  # Repeat sequence to avoid StopIteration

        memories = os.recall(
            query="test query",
            threshold=0.7,
            min_results=3,
            adaptive_threshold=True,
            use_semantic_expansion=False  # Disable expansion for this test
        )

        # Verify we got results after lowering threshold
        assert len(memories) == 3
        assert all(0.6 <= m.similarity <= 0.7 for m in memories)
        
        # Verify multiple search attempts were made
        assert mock_requests.call_count == 3
        
        # Verify thresholds in the requests
        calls = mock_requests.call_args_list
        assert abs(float(calls[0].kwargs["json"]["variables"]["args"]["match_threshold"]) - 0.7) < 1e-10
        assert abs(float(calls[1].kwargs["json"]["variables"]["args"]["match_threshold"]) - 0.65) < 1e-10
        assert abs(float(calls[2].kwargs["json"]["variables"]["args"]["match_threshold"]) - 0.6) < 1e-10

    def test_combined_semantic_and_adaptive(self, os, mock_requests, mock_openai):
        """Test combination of semantic expansion and adaptive threshold."""
        # Mock a sequence of results
        responses = [
            # Original query, first threshold
            {"data": {"search_memories": []}},
            # Original query, lowered threshold
            {
                "data": {
                    "search_memories": [
                        {**TEST_MEMORY, "id": "1", "similarity": 0.65}
                    ]
                }
            },
            # Variation query, first threshold
            {"data": {"search_memories": []}},
            # Variation query, lowered threshold
            {
                "data": {
                    "search_memories": [
                        {**TEST_MEMORY, "id": "2", "similarity": 0.62}
                    ]
                }
            }
        ]
        mock_requests.return_value.json.side_effect = responses * 3  # Ensure enough responses

        memories = os.recall(
            query="programming language",
            threshold=0.7,
            min_results=2,
            adaptive_threshold=True,
            use_semantic_expansion=True
        )

        # Verify results
        assert len(memories) == 2
        assert abs(memories[0].similarity - 0.65) < 1e-10  # Best match
        assert abs(memories[1].similarity - 0.62) < 1e-10  # Second best
        
        # Verify both expansion and adaptive threshold were used
        assert mock_openai.chat.completions.create.call_count == 1
        assert mock_requests.call_count == 6  # Account for semantic expansion requests
    
    def test_forget(self, os, mock_requests):
        """Test deleting a memory."""
        setup_mock_response(mock_requests, {
            "delete_memories_by_pk": {"id": TEST_MEMORY["id"]}
        })
        
        result = os.forget(TEST_MEMORY["id"])
        assert result is True
        
        # Verify GraphQL mutation
        verify_graphql_query(mock_requests, "mutation Forget")

class TestMemoryEdges:
    """Tests for memory edge operations."""
    
    def test_link_memories(self, os, mock_requests):
        """Test creating a link between memories."""
        mock_requests.return_value.json.return_value = {
            "data": {
                "insert_memory_edges_one": TEST_MEMORY_EDGE
            }
        }
        
        edge = os.link_memories(
            source_memory_id="test-memory-id-1",
            target_memory_id="test-memory-id-2",
            relationship="related_to"
        )
        
        assert isinstance(edge, MemoryEdge)
        assert edge.id == TEST_MEMORY_EDGE["id"]
        assert edge.source_memory == TEST_MEMORY_EDGE["source_memory"]
        assert edge.target_memory == TEST_MEMORY_EDGE["target_memory"]
        assert edge.relationship == TEST_MEMORY_EDGE["relationship"]
        assert edge.weight == TEST_MEMORY_EDGE["weight"]
    
    def test_unlink_memories(self, os, mock_requests):
        """Test removing links between memories."""
        mock_requests.return_value.json.return_value = {
            "data": {
                "delete_memory_edges": {
                    "affected_rows": 1
                }
            }
        }
        
        result = os.unlink_memories(
            source_memory_id="test-memory-id-1",
            target_memory_id="test-memory-id-2",
            relationship="related_to"
        )
        
        assert result is True
        
        # Test with no relationship specified
        result = os.unlink_memories(
            source_memory_id="test-memory-id-1",
            target_memory_id="test-memory-id-2"
        )
        
        assert result is True
    
    def test_update_memory(self, os, mock_requests, mock_openai):
        """Test updating a memory with versioning."""
        # Mock getting the old memory
        mock_requests.return_value.json.side_effect = [
            {
                "data": {
                    "memories_by_pk": TEST_MEMORY
                }
            },
            {
                "data": {
                    "insert_memories_one": {
                        **TEST_MEMORY,
                        "id": "test-memory-id-2",
                        "content": "Updated content"
                    }
                }
            },
            {
                "data": {
                    "insert_memory_edges_one": {
                        **TEST_MEMORY_EDGE,
                        "relationship": "version_of"
                    }
                }
            }
        ]
        
        new_memory = os.update_memory(
            memory_id="test-memory-id",
            content="Updated content",
            create_version_edge=True
        )
        
        assert isinstance(new_memory, Memory)
        assert new_memory.id == "test-memory-id-2"
        assert new_memory.content == "Updated content"
        
        # Test without version edge
        mock_requests.return_value.json.side_effect = [
            {
                "data": {
                    "memories_by_pk": TEST_MEMORY
                }
            },
            {
                "data": {
                    "insert_memories_one": {
                        **TEST_MEMORY,
                        "id": "test-memory-id-3",
                        "content": "Updated content"
                    }
                }
            }
        ]
        
        new_memory = os.update_memory(
            memory_id="test-memory-id",
            content="Updated content",
            create_version_edge=False
        )
        
        assert isinstance(new_memory, Memory)
        assert new_memory.id == "test-memory-id-3"
    
    def test_get_connected_memories(self, os, mock_requests):
        """Test getting connected memories."""
        mock_requests.return_value.json.return_value = {
            "data": {
                "get_connected_memories": [
                    {
                        "source_id": "test-memory-id-1",
                        "target_id": "test-memory-id-2",
                        "relationship": "related_to",
                        "weight": 1.0,
                        "depth": 1
                    }
                ]
            }
        }
        
        connections = os.get_connected_memories(
            memory_id="test-memory-id-1",
            relationship="related_to",
            max_depth=2
        )
        
        assert len(connections) == 1
        assert connections[0]["source_id"] == "test-memory-id-1"
        assert connections[0]["target_id"] == "test-memory-id-2"
        assert connections[0]["relationship"] == "related_to"
        assert connections[0]["weight"] == 1.0
        assert connections[0]["depth"] == 1

class TestErrorHandling:
    """Tests for error handling scenarios."""
    
    def test_invalid_api_key(self, mock_requests):
        """Test handling of invalid API key."""
        mock_requests.return_value.status_code = 401
        mock_requests.return_value.raise_for_status.side_effect = Exception("Unauthorized")
        
        os = MeshOS(
            api_key="invalid",
            openai_api_key="test-key"  # Provide OpenAI key to avoid that error
        )
        
        with pytest.raises(Exception, match="Unauthorized"):
            os.get_agent("any-id")
    
    def test_missing_openai_key(self):
        """Test handling of missing OpenAI key."""
        with patch.dict(os_module.environ, {}, clear=True):  # Clear env vars
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                MeshOS(openai_api_key=None)
    
    def test_failed_embedding(self, os, mock_openai):
        """Test handling of OpenAI embedding failure."""
        # Set up the mock to raise an exception for embeddings.create
        mock_openai.embeddings.create.side_effect = Exception("OpenAI API Error")

        with pytest.raises(Exception, match="OpenAI API Error"):
            os.remember(
                content="test content",
                agent_id=TEST_AGENT["id"]
            )
    
    def test_graphql_error(self, os, mock_requests):
        """Test handling of GraphQL errors."""
        mock_requests.return_value.json.return_value = {
            "errors": [{"message": "GraphQL Error"}]
        }
        
        with pytest.raises(GraphQLError, match="GraphQL Error"):
            os.get_agent("any-id") 