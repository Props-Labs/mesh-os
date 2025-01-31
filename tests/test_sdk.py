"""
Tests for the PropsOS SDK.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest
from openai import OpenAI

from props_os import PropsOS
from props_os.core.client import Agent, GraphQLError, Memory

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
    "metadata": {"type": "test"},
    "embedding": [0.1] * 1536,  # Matches OpenAI's embedding size
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}

@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        yield

@pytest.fixture
def mock_openai():
    """Mock OpenAI's embedding creation."""
    mock_embeddings = MagicMock()
    mock_embeddings.create.return_value = MagicMock(
        data=[
            MagicMock(
                embedding=[0.1] * 1536,
                index=0
            )
        ]
    )
    
    mock_client = MagicMock()
    mock_client.embeddings = mock_embeddings
    
    with patch("openai.OpenAI", return_value=mock_client) as mock:
        yield mock_embeddings.create

@pytest.fixture
def mock_requests():
    """Mock all requests to Hasura."""
    with patch("requests.post") as mock:
        mock.return_value.status_code = 200
        yield mock

@pytest.fixture
def props(mock_openai, mock_requests):
    """Create a PropsOS instance with mocked dependencies."""
    return PropsOS(
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

class TestAgentManagement:
    """Tests for agent-related operations."""
    
    def test_register_agent(self, props, mock_requests):
        """Test registering a new agent."""
        setup_mock_response(mock_requests, {
            "insert_agents_one": TEST_AGENT
        })
        
        agent = props.register_agent(
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
    
    def test_unregister_agent(self, props, mock_requests):
        """Test unregistering an agent."""
        setup_mock_response(mock_requests, {
            "delete_agents_by_pk": {"id": TEST_AGENT["id"]}
        })
        
        result = props.unregister_agent(TEST_AGENT["id"])
        assert result is True
        
        # Verify GraphQL mutation
        verify_graphql_query(mock_requests, "mutation UnregisterAgent")
    
    def test_get_agent(self, props, mock_requests):
        """Test retrieving agent details."""
        setup_mock_response(mock_requests, {
            "agents_by_pk": TEST_AGENT
        })
        
        agent = props.get_agent(TEST_AGENT["id"])
        assert isinstance(agent, Agent)
        assert agent.id == TEST_AGENT["id"]
        
        # Verify GraphQL query
        verify_graphql_query(mock_requests, "query GetAgent")

class TestMemoryOperations:
    """Tests for memory-related operations."""
    
    def test_remember(self, props, mock_requests, mock_openai):
        """Test storing a new memory."""
        setup_mock_response(mock_requests, {
            "insert_memories_one": TEST_MEMORY
        })
        
        memory = props.remember(
            content=TEST_MEMORY["content"],
            agent_id=TEST_MEMORY["agent_id"],
            metadata=TEST_MEMORY["metadata"]
        )
        
        assert isinstance(memory, Memory)
        assert memory.id == TEST_MEMORY["id"]
        assert memory.content == TEST_MEMORY["content"]
        assert memory.metadata == TEST_MEMORY["metadata"]
        
        # Verify OpenAI embedding was requested
        mock_openai.assert_called_once()
        
        # Verify GraphQL mutation
        verify_graphql_query(mock_requests, "mutation Remember")
    
    def test_recall_with_filters(self, props, mock_requests, mock_openai):
        """Test searching memories with filters."""
        setup_mock_response(mock_requests, {
            "search_memories": [TEST_MEMORY]
        })
        
        filters = {
            "type": "test",
            "confidence": {"_gt": 0.8},
            "created_at": {"_gte": "2024-01-01"},
            "tags": {"_contains": ["important"]}
        }
        
        memories = props.recall(
            query="test query",
            agent_id=TEST_MEMORY["agent_id"],
            limit=5,
            threshold=0.7,
            filters=filters
        )
        
        assert isinstance(memories, list)
        assert len(memories) == 1
        assert isinstance(memories[0], Memory)
        assert memories[0].id == TEST_MEMORY["id"]
        
        # Verify OpenAI embedding was requested
        mock_openai.assert_called_once()
        
        # Verify GraphQL query with filters
        verify_graphql_query(mock_requests, "query SearchMemories")
        variables = mock_requests.call_args[1]["json"]["variables"]
        assert "where" in variables
        assert variables["where"].get("type") == {"_eq": "test"}
    
    def test_forget(self, props, mock_requests):
        """Test deleting a memory."""
        setup_mock_response(mock_requests, {
            "delete_memories_by_pk": {"id": TEST_MEMORY["id"]}
        })
        
        result = props.forget(TEST_MEMORY["id"])
        assert result is True
        
        # Verify GraphQL mutation
        verify_graphql_query(mock_requests, "mutation Forget")

class TestErrorHandling:
    """Tests for error handling scenarios."""
    
    def test_invalid_api_key(self, mock_requests):
        """Test handling of invalid API key."""
        mock_requests.return_value.status_code = 401
        mock_requests.return_value.raise_for_status.side_effect = Exception("Unauthorized")
        
        props = PropsOS(
            api_key="invalid",
            openai_api_key="test-key"  # Provide OpenAI key to avoid that error
        )
        
        with pytest.raises(Exception, match="Unauthorized"):
            props.get_agent("any-id")
    
    def test_missing_openai_key(self):
        """Test handling of missing OpenAI key."""
        with patch.dict(os.environ, {}, clear=True):  # Clear env vars
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                PropsOS(openai_api_key=None)
    
    def test_failed_embedding(self, props, mock_openai):
        """Test handling of OpenAI embedding failure."""
        mock_openai.side_effect = Exception("OpenAI API Error")
        
        with pytest.raises(Exception, match="OpenAI API Error"):
            props.remember(
                content="test content",
                agent_id=TEST_AGENT["id"]  # Provide required agent_id
            )
    
    def test_graphql_error(self, props, mock_requests):
        """Test handling of GraphQL errors."""
        mock_requests.return_value.json.return_value = {
            "errors": [{"message": "GraphQL Error"}]
        }
        
        with pytest.raises(GraphQLError, match="GraphQL Error"):
            props.get_agent("any-id") 