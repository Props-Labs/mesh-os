"""
Tests for the MeshOS SDK.
"""
import json
import unittest
from datetime import datetime, timezone
from typing import Dict, List
from unittest.mock import MagicMock, patch, call
import os as os_module  # Rename to avoid conflict

import pytest
from openai import OpenAI

from mesh_os import MeshOS
from mesh_os.core.client import Agent, GraphQLError, Memory, MemoryEdge, InvalidSlugError
from mesh_os.core.taxonomy import DataType, EdgeType, MemoryMetadata, EdgeMetadata

# Test data
TEST_AGENT = {
    "id": "test-agent-id",
    "name": "TestAgent",
    "description": "Test description",
    "metadata": {"capabilities": ["test"]},
    "status": "active",
    "slug": "test-agent"  # Add default slug
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
    # For mock_calls, we need to access the kwargs differently
    if isinstance(mock_requests, unittest.mock._Call):
        if hasattr(mock_requests, 'kwargs') and 'json' in mock_requests.kwargs:
            request_data = mock_requests.kwargs["json"]
        elif len(mock_requests) >= 2 and isinstance(mock_requests[1], dict):
            request_data = mock_requests[1].get("json", {})
        else:
            return  # Skip verification for non-request calls
    else:
        request_data = mock_requests.call_args[1]["json"]
    
    if request_data and isinstance(request_data.get("query"), str):
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
        # First mock the get_agent_by_slug response (empty result)
        setup_mock_response(mock_requests, {
            "agents": []
        })
        # Then mock the insert response
        mock_requests.return_value.json.side_effect = [
            {"data": {"agents": []}},  # First call (get_agent_by_slug)
            {"data": {"insert_agents_one": TEST_AGENT}}  # Second call (insert)
        ]
        
        agent = os.register_agent(
            name=TEST_AGENT["name"],
            description=TEST_AGENT["description"],
            metadata=TEST_AGENT["metadata"],
            slug=TEST_AGENT["slug"]
        )
        
        assert isinstance(agent, Agent)
        assert agent.id == TEST_AGENT["id"]
        assert agent.name == TEST_AGENT["name"]
        assert agent.metadata == TEST_AGENT["metadata"]
        assert agent.slug == TEST_AGENT["slug"]
        
        # Verify both queries were made
        assert mock_requests.call_count == 2
        
        # Find the actual request calls in the mock_calls
        request_calls = []
        for call in mock_requests.mock_calls:
            if isinstance(call, unittest.mock._Call):
                if len(call) >= 2 and isinstance(call[1], dict) and "json" in call[1]:
                    request_calls.append(call)
                elif hasattr(call, "kwargs") and "json" in call.kwargs:
                    request_calls.append(call)
        
        assert len(request_calls) == 2
        verify_graphql_query(request_calls[0], "query GetAgentBySlug")
        verify_graphql_query(request_calls[1], "mutation RegisterAgent")
    
    def test_register_agent_invalid_slug(self, os, mock_requests):
        """Test registering an agent with invalid slug."""
        with pytest.raises(InvalidSlugError):
            os.register_agent(
                name=TEST_AGENT["name"],
                description=TEST_AGENT["description"],
                slug="Invalid Slug"  # Contains spaces and capitals
            )
    
    def test_register_agent_existing_slug(self, os, mock_requests):
        """Test registering an agent with existing slug returns existing agent."""
        # First mock the get_agent_by_slug response
        setup_mock_response(mock_requests, {
            "agents": [TEST_AGENT]
        })
        
        agent = os.register_agent(
            name="Different Name",
            description="Different description",
            slug=TEST_AGENT["slug"]
        )
        
        assert agent.id == TEST_AGENT["id"]
        assert agent.name == TEST_AGENT["name"]  # Should get existing agent's name
        
        # Verify only the get_agent_by_slug query was made
        verify_graphql_query(mock_requests.mock_calls[0], "query GetAgentBySlug")
        assert mock_requests.call_count == 1  # No insert attempt should be made
    
    def test_get_agent_by_slug(self, os, mock_requests):
        """Test retrieving agent by slug."""
        setup_mock_response(mock_requests, {
            "agents": [TEST_AGENT]
        })
        
        agent = os.get_agent_by_slug(TEST_AGENT["slug"])
        assert isinstance(agent, Agent)
        assert agent.id == TEST_AGENT["id"]
        assert agent.slug == TEST_AGENT["slug"]
        
        # Verify GraphQL query
        verify_graphql_query(mock_requests.mock_calls[0], "query GetAgentBySlug")
    
    def test_get_agent_by_invalid_slug(self, os, mock_requests):
        """Test retrieving agent with invalid slug format."""
        with pytest.raises(InvalidSlugError):
            os.get_agent_by_slug("Invalid Slug")
    
    def test_get_agent_by_nonexistent_slug(self, os, mock_requests):
        """Test retrieving agent with nonexistent slug."""
        setup_mock_response(mock_requests, {
            "agents": []
        })
        
        agent = os.get_agent_by_slug("nonexistent-agent")
        assert agent is None
    
    def test_unregister_agent(self, os, mock_requests):
        """Test unregistering an agent."""
        setup_mock_response(mock_requests, {
            "delete_agents_by_pk": {"id": TEST_AGENT["id"]}
        })
        
        result = os.unregister_agent(TEST_AGENT["id"])
        assert result is True
        
        # Verify GraphQL mutation
        verify_graphql_query(mock_requests.mock_calls[0], "mutation UnregisterAgent")
    
    def test_get_agent(self, os, mock_requests):
        """Test retrieving agent details."""
        setup_mock_response(mock_requests, {
            "agents_by_pk": TEST_AGENT
        })
        
        agent = os.get_agent(TEST_AGENT["id"])
        assert isinstance(agent, Agent)
        assert agent.id == TEST_AGENT["id"]
        
        # Verify GraphQL query
        verify_graphql_query(mock_requests.mock_calls[0], "query GetAgent")

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
        verify_graphql_query(mock_requests.mock_calls[0], "mutation Remember")
    
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
        verify_graphql_query(mock_requests.mock_calls[0], "query SearchMemories")
        variables = mock_requests.call_args[1]["json"]["variables"]
        assert "args" in variables

    def test_semantic_expansion(self, os, mock_requests, mock_openai):
        """Test query semantic expansion."""
        # Set up responses to trigger semantic expansion:
        # 1. Initial try with high threshold - no results
        # 2. Try with adaptive thresholds - no results all the way down to min_threshold
        # 3. Try semantic variations with original threshold - get results
        base_response = {"data": {"search_memories": []}}
        success_response = {
            "data": {
                "search_memories": [
                    {**TEST_MEMORY, "id": "1", "similarity": 0.85},
                    {**TEST_MEMORY, "id": "2", "similarity": 0.75}
                ]
            }
        }
        
        # Create sequence of responses:
        # 1. Empty for original query at 0.7
        # 2. Empty for all adaptive thresholds (0.65 down to 0.3)
        # 3. Empty for first semantic variation at 0.7
        # 4. Success for second semantic variation at 0.7
        responses = [base_response] * 9  # Empty responses for initial try and adaptive thresholds (0.7 -> 0.3)
        responses.append(base_response)    # First semantic variation fails
        responses.append(success_response) # Second semantic variation succeeds
        mock_requests.return_value.json.side_effect = responses * 3  # Ensure enough responses

        # Set up chat completion mock to return variations
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="alternative programming syntax\ncoding language"
                    )
                )
            ]
        )

        memories = os.recall(
            query="programming language",
            use_semantic_expansion=True,
            threshold=0.7,  # Start with high threshold
            limit=4,
            min_results=1  # Just need one good result
        )

        # Verify we got the expected results
        assert len(memories) == 2  # We get the results from semantic expansion
        assert [m.id for m in memories] == ["1", "2"]  # Results from variation
        assert abs(memories[0].similarity - 0.85) < 1e-10  # Best match
        
        # Verify semantic expansion was used
        assert mock_openai.chat.completions.create.call_count == 1
        messages = mock_openai.chat.completions.create.call_args[1]["messages"]
        assert any("programming language" in msg["content"] for msg in messages)
        
        # Verify search progression
        request_calls = []
        for call in mock_requests.mock_calls:
            if isinstance(call, unittest.mock._Call):
                if hasattr(call, "kwargs") and "json" in call.kwargs:
                    request_calls.append(call)
        
        # 1. First call should use original threshold (0.7)
        assert abs(float(request_calls[0].kwargs["json"]["variables"]["args"]["match_threshold"]) - 0.7) < 1e-10
        
        # 2. Next calls should be adaptive threshold reduction with original query
        # We expect: 0.7 -> 0.65 -> 0.6 -> 0.55 -> 0.5 -> 0.45 -> 0.4 -> 0.35 -> 0.3
        adaptive_calls = request_calls[1:8]  # Check adaptive threshold calls
        for i, call in enumerate(adaptive_calls):
            threshold = float(call.kwargs["json"]["variables"]["args"]["match_threshold"])
            expected = 0.7 - ((i + 1) * 0.05)  # 0.65, 0.6, 0.55, ...
            assert abs(threshold - expected) < 1e-10
            
        # 3. Then we should try semantic variations with original threshold
        semantic_calls = request_calls[8:10]  # Check semantic variation calls
        for call in semantic_calls:
            threshold = float(call.kwargs["json"]["variables"]["args"]["match_threshold"])
            assert abs(threshold - 0.7) < 1e-10  # Should use original threshold

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
        request_calls = []
        for call in mock_requests.mock_calls:
            if isinstance(call, unittest.mock._Call):
                if hasattr(call, "kwargs") and "json" in call.kwargs:
                    request_calls.append(call)
        
        assert len(request_calls) == 3
        assert abs(float(request_calls[0].kwargs["json"]["variables"]["args"]["match_threshold"]) - 0.7) < 1e-10
        assert abs(float(request_calls[1].kwargs["json"]["variables"]["args"]["match_threshold"]) - 0.65) < 1e-10
        assert abs(float(request_calls[2].kwargs["json"]["variables"]["args"]["match_threshold"]) - 0.6) < 1e-10

    def test_combined_semantic_and_adaptive(self, os, mock_requests, mock_openai):
        """Test combination of semantic expansion and adaptive threshold."""
        # Mock a sequence of results
        responses = [
            # Original query, first threshold (0.7)
            {"data": {"search_memories": []}},
            # Original query, lowered threshold (0.65)
            {
                "data": {
                    "search_memories": [
                        {**TEST_MEMORY, "id": "1", "similarity": 0.65}
                    ]
                }
            }
        ]
        mock_requests.return_value.json.side_effect = responses * 3  # Ensure enough responses

        memories = os.recall(
            query="programming language",
            threshold=0.7,
            min_results=1,  # Only need one result
            adaptive_threshold=True,
            use_semantic_expansion=True
        )

        # Verify results - we should get the result from adaptive threshold
        # before even trying semantic expansion
        assert len(memories) == 1
        assert abs(memories[0].similarity - 0.65) < 1e-10  # Best match
        
        # Verify semantic expansion was NOT used since we found results with just adaptive threshold
        assert mock_openai.chat.completions.create.call_count == 0
        assert mock_requests.call_count == 2  # Initial try + one threshold reduction
    
    def test_forget(self, os, mock_requests):
        """Test deleting a memory."""
        setup_mock_response(mock_requests, {
            "delete_memories_by_pk": {"id": TEST_MEMORY["id"]}
        })
        
        result = os.forget(TEST_MEMORY["id"])
        assert result is True
        
        # Verify GraphQL mutation
        verify_graphql_query(mock_requests.mock_calls[0], "mutation Forget")

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