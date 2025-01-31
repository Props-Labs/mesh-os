"""
Tests for the VentureOS SDK.
"""
import json
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from venture_os.core.sdk import Agent, AgentMemorySDK, Memory


@pytest.fixture
def sdk():
    """Create a SDK instance with mocked requests."""
    return AgentMemorySDK(
        hasura_url="http://test-url",
        hasura_admin_secret="test-secret"
    )


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    mock = MagicMock()
    mock.json.return_value = {}
    mock.raise_for_status.return_value = None
    return mock


def test_register_agent(sdk, mock_response):
    """Test registering a new agent."""
    mock_response.json.return_value = {
        "data": {
            "insert_agents_one": {
                "id": "test-id",
                "name": "TestAgent",
                "description": "Test description",
                "status": "active",
                "data": {"key": "value"}
            }
        }
    }

    with patch("requests.post", return_value=mock_response):
        agent = sdk.register_agent(
            name="TestAgent",
            description="Test description",
            data={"key": "value"}
        )

        assert isinstance(agent, Agent)
        assert agent.id == "test-id"
        assert agent.name == "TestAgent"
        assert agent.description == "Test description"
        assert agent.status == "active"
        assert agent.data == {"key": "value"}


def test_add_memory(sdk, mock_response):
    """Test adding a new memory."""
    mock_response.json.return_value = {
        "data": {
            "insert_memories_one": {
                "id": "test-id",
                "agent_id": "agent-id",
                "memory_type": "note",
                "data": {"text": "test"},
                "metadata": {"source": "test"},
                "content_vector": [0.1, 0.2]
            }
        }
    }

    with patch("requests.post", return_value=mock_response):
        memory = sdk.add_memory(
            memory_type="note",
            data={"text": "test"},
            agent_id="agent-id",
            metadata={"source": "test"},
            content_vector=[0.1, 0.2]
        )

        assert isinstance(memory, Memory)
        assert memory.id == "test-id"
        assert memory.agent_id == "agent-id"
        assert memory.memory_type == "note"
        assert memory.data == {"text": "test"}
        assert memory.metadata == {"source": "test"}
        assert memory.content_vector == [0.1, 0.2]


def test_search_memories(sdk, mock_response):
    """Test searching memories."""
    mock_response.json.return_value = {
        "data": {
            "memories": [
                {
                    "id": "test-id-1",
                    "agent_id": "agent-id",
                    "memory_type": "note",
                    "data": {"text": "test1"},
                    "metadata": {"source": "test"},
                    "content_vector": [0.1, 0.2]
                },
                {
                    "id": "test-id-2",
                    "agent_id": "agent-id",
                    "memory_type": "note",
                    "data": {"text": "test2"},
                    "metadata": {"source": "test"},
                    "content_vector": [0.3, 0.4]
                }
            ]
        }
    }

    with patch("requests.post", return_value=mock_response):
        memories = sdk.search_memories(
            query_vector=[0.1, 0.2],
            limit=2,
            agent_id="agent-id"
        )

        assert isinstance(memories, list)
        assert len(memories) == 2
        assert all(isinstance(m, Memory) for m in memories)
        assert memories[0].id == "test-id-1"
        assert memories[1].id == "test-id-2"


def test_delete_memory(sdk, mock_response):
    """Test deleting a memory."""
    mock_response.json.return_value = {
        "data": {
            "delete_memories_by_pk": {
                "id": "test-id"
            }
        }
    }

    with patch("requests.post", return_value=mock_response):
        result = sdk.delete_memory("test-id")
        assert result is True


def test_update_agent_status(sdk, mock_response):
    """Test updating agent status."""
    mock_response.json.return_value = {
        "data": {
            "update_agents_by_pk": {
                "id": "test-id",
                "name": "TestAgent",
                "description": "Test description",
                "status": "busy",
                "data": {"key": "value"}
            }
        }
    }

    with patch("requests.post", return_value=mock_response):
        agent = sdk.update_agent_status("test-id", "busy")
        assert isinstance(agent, Agent)
        assert agent.id == "test-id"
        assert agent.status == "busy" 