"""
Tests for the MeshOS CLI.
"""
import json
import uuid
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from mesh_os.cli.main import cli, validate_uuid, validate_metadata, validate_memory_metadata
from mesh_os.core.taxonomy import DataType, EdgeType, KnowledgeSubtype
from mesh_os.core.client import InvalidSlugError

# Test data with fixed UUIDs for consistency
TEST_AGENT = {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "TestAgent",
    "description": "Test description",
    "metadata": {"capabilities": ["test"]},
    "status": "active",
    "slug": "test-agent"  # Add default slug
}

TEST_MEMORY = {
    "id": "123e4567-e89b-12d3-a456-426614174001",
    "agent_id": TEST_AGENT["id"],
    "content": "Test memory content",
    "metadata": {
        "type": "knowledge",
        "subtype": "dataset",
        "tags": ["test"],
        "version": 1
    },
    "embedding": [0.1] * 1536,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}

TEST_MEMORY_EDGE = {
    "id": "123e4567-e89b-12d3-a456-426614174002",
    "source_memory": "123e4567-e89b-12d3-a456-426614174003",
    "target_memory": "123e4567-e89b-12d3-a456-426614174004",
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

@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()

@pytest.fixture
def mock_client():
    """Mock the MeshOS client."""
    with patch("mesh_os.cli.main.get_client") as mock:
        yield mock.return_value

@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables."""
    with patch.dict("os.environ", {
        "OPENAI_API_KEY": "test-key",
        "HASURA_URL": "http://test-url",
        "HASURA_ADMIN_SECRET": "test-secret"
    }):
        yield

class TestValidation:
    """Tests for validation functions."""
    
    def test_validate_uuid(self):
        """Test UUID validation."""
        valid_uuid = TEST_AGENT["id"]
        assert validate_uuid(None, None, valid_uuid) == valid_uuid
        
        with pytest.raises(click.BadParameter, match="Invalid UUID format"):
            validate_uuid(None, None, "not-a-uuid")
    
    def test_validate_metadata(self):
        """Test metadata validation."""
        # Test valid metadata
        assert validate_metadata('{"key": "value"}') == {"key": "value"}
        
        # Test None input
        assert validate_metadata(None) is None
        
        # Test non-dict JSON
        with pytest.raises(click.BadParameter, match="Metadata must be a JSON object"):
            validate_metadata('"string"')
        
        # Test invalid JSON
        with pytest.raises(click.BadParameter, match="Invalid JSON format"):
            validate_metadata("{invalid json}")
    
    def test_validate_memory_metadata(self):
        """Test memory metadata validation."""
        valid_metadata = {
            "type": "knowledge",
            "subtype": "dataset",
            "tags": ["test"],
            "version": 1
        }
        assert validate_memory_metadata(valid_metadata) == valid_metadata
        
        # Test missing type
        with pytest.raises(click.BadParameter, match="must include 'type' field"):
            validate_memory_metadata({"subtype": "dataset"})
        
        # Test missing subtype
        with pytest.raises(click.BadParameter, match="must include 'subtype' field"):
            validate_memory_metadata({"type": "knowledge"})
        
        # Test invalid type
        with pytest.raises(click.BadParameter):
            validate_memory_metadata({"type": "invalid", "subtype": "dataset"})
        
        # Test invalid subtype
        with pytest.raises(click.BadParameter):
            validate_memory_metadata({"type": "knowledge", "subtype": "invalid"})

class TestAgentCommands:
    """Tests for agent-related CLI commands."""
    
    def test_register_agent(self, runner, mock_client):
        """Test registering a new agent."""
        mock_client.register_agent.return_value = MagicMock(**TEST_AGENT)
        
        result = runner.invoke(cli, [
            "agent", "register",
            "TestAgent",
            "--description", "Test description",
            "--metadata", json.dumps(TEST_AGENT["metadata"]),
            "--slug", "test-agent"
        ])
        
        assert result.exit_code == 0
        assert "Agent registered" in result.output
        # Remove any newlines from the output before checking
        output = result.output.replace("\n", "")
        assert f"(slug: {TEST_AGENT['slug']})" in output
        mock_client.register_agent.assert_called_once_with(
            "TestAgent",
            "Test description",
            TEST_AGENT["metadata"],
            "test-agent"
        )
    
    def test_register_agent_invalid_slug(self, runner, mock_client):
        """Test registering an agent with invalid slug."""
        mock_client.register_agent.side_effect = InvalidSlugError("Invalid slug format")
        
        result = runner.invoke(cli, [
            "agent", "register",
            "TestAgent",
            "--slug", "Invalid Slug"
        ])
        
        assert result.exit_code == 1
        assert "Invalid slug format" in result.output
    
    def test_unregister_agent_by_slug(self, runner, mock_client):
        """Test unregistering an agent using slug."""
        mock_client.get_agent_by_slug.return_value = MagicMock(**TEST_AGENT)
        mock_client.unregister_agent.return_value = True
        
        result = runner.invoke(cli, ["agent", "unregister", "test-agent"])
        
        assert result.exit_code == 0
        assert "unregistered" in result.output
        mock_client.get_agent_by_slug.assert_called_once_with("test-agent")
        mock_client.unregister_agent.assert_called_once_with(TEST_AGENT["id"])
    
    def test_unregister_agent_nonexistent_slug(self, runner, mock_client):
        """Test unregistering an agent with nonexistent slug."""
        mock_client.get_agent_by_slug.return_value = None
        mock_client.get_agent.return_value = None
        
        result = runner.invoke(cli, ["agent", "unregister", "nonexistent-agent"])
        
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_update_agent_status_by_slug(self, runner, mock_client):
        """Test updating an agent's status using slug."""
        mock_client.get_agent_by_slug.return_value = MagicMock(**TEST_AGENT)
        updated_agent = dict(TEST_AGENT)
        updated_agent["status"] = "inactive"
        mock_client.update_agent_status.return_value = MagicMock(**updated_agent)
        
        result = runner.invoke(cli, ["agent", "update-status", "test-agent", "inactive"])
        
        assert result.exit_code == 0
        assert "status updated to: inactive" in result.output
        mock_client.get_agent_by_slug.assert_called_once_with("test-agent")
        mock_client.update_agent_status.assert_called_once_with(TEST_AGENT["id"], "inactive")
    
    def test_update_agent_status_by_id(self, runner, mock_client):
        """Test updating an agent's status using UUID."""
        mock_client.get_agent_by_slug.return_value = None
        mock_client.get_agent.return_value = MagicMock(**TEST_AGENT)
        updated_agent = dict(TEST_AGENT)
        updated_agent["status"] = "error"
        mock_client.update_agent_status.return_value = MagicMock(**updated_agent)
        
        result = runner.invoke(cli, ["agent", "update-status", TEST_AGENT["id"], "error"])
        
        assert result.exit_code == 0
        assert "status updated to: error" in result.output
        mock_client.get_agent.assert_called_once_with(TEST_AGENT["id"])
        mock_client.update_agent_status.assert_called_once_with(TEST_AGENT["id"], "error")
    
    def test_update_agent_status_invalid_status(self, runner, mock_client):
        """Test updating an agent with invalid status."""
        mock_client.get_agent_by_slug.return_value = MagicMock(**TEST_AGENT)
        
        result = runner.invoke(cli, ["agent", "update-status", "test-agent", "invalid"])
        
        assert result.exit_code == 1
        assert "Invalid status" in result.output
        mock_client.update_agent_status.assert_not_called()
    
    def test_update_agent_status_nonexistent_agent(self, runner, mock_client):
        """Test updating status of nonexistent agent."""
        mock_client.get_agent_by_slug.return_value = None
        mock_client.get_agent.return_value = None
        
        result = runner.invoke(cli, ["agent", "update-status", "nonexistent-agent", "active"])
        
        assert result.exit_code == 1
        assert "not found" in result.output
        mock_client.update_agent_status.assert_not_called()

class TestMemoryCommands:
    """Tests for memory-related CLI commands."""
    
    def test_remember(self, runner, mock_client):
        """Test storing a new memory."""
        mock_client.remember.return_value = MagicMock(**TEST_MEMORY)
        
        result = runner.invoke(cli, [
            "memory", "remember",
            "Test content",
            "--agent-id", TEST_AGENT["id"],
            "--metadata", json.dumps(TEST_MEMORY["metadata"])
        ])
        
        assert result.exit_code == 0
        assert "Memory stored" in result.output
        mock_client.remember.assert_called_once()
    
    def test_recall(self, runner, mock_client):
        """Test searching memories."""
        mock_client.recall.return_value = [MagicMock(**TEST_MEMORY)]
        
        result = runner.invoke(cli, [
            "memory", "recall",
            "test query",
            "--agent-id", TEST_AGENT["id"],
            "--limit", "5",
            "--threshold", "0.7",
            "--filter", "type=knowledge",
            "--filter", "confidence._gt=0.8"
        ])
        
        assert result.exit_code == 0
        assert "Found 1 matching" in result.output
        mock_client.recall.assert_called_once()
    
    def test_forget(self, runner, mock_client):
        """Test deleting a memory."""
        mock_client.forget.return_value = True
        
        result = runner.invoke(cli, ["memory", "forget", TEST_MEMORY["id"]])
        
        assert result.exit_code == 0
        assert "deleted" in result.output
        mock_client.forget.assert_called_once_with(TEST_MEMORY["id"])

class TestMemoryEdgeCommands:
    """Tests for memory edge-related CLI commands."""
    
    def test_link_memories(self, runner, mock_client):
        """Test creating a link between memories."""
        mock_client.link_memories.return_value = MagicMock(**TEST_MEMORY_EDGE)
        
        result = runner.invoke(cli, [
            "memory", "link",
            TEST_MEMORY_EDGE["source_memory"],
            TEST_MEMORY_EDGE["target_memory"],
            "--relationship", "related_to",
            "--weight", "1.0"
        ])
        
        assert result.exit_code == 0
        assert "Created related_to link" in result.output
        mock_client.link_memories.assert_called_once()
    
    def test_unlink_memories(self, runner, mock_client):
        """Test removing links between memories."""
        mock_client.unlink_memories.return_value = True
        
        result = runner.invoke(cli, [
            "memory", "unlink",
            TEST_MEMORY_EDGE["source_memory"],
            TEST_MEMORY_EDGE["target_memory"],
            "--relationship", "related_to"
        ])
        
        assert result.exit_code == 0
        assert "Removed link" in result.output
        mock_client.unlink_memories.assert_called_once()

class TestErrorHandling:
    """Tests for CLI error handling."""
    
    def test_invalid_uuid(self, runner, mock_client):
        """Test handling of invalid UUIDs."""
        # Mock get_agent_by_slug to return None (not found)
        mock_client.get_agent_by_slug.side_effect = InvalidSlugError("Invalid slug format")
        
        result = runner.invoke(cli, ["agent", "unregister", "not-a-uuid"], catch_exceptions=False)
        assert result.exit_code == 1
        assert "Invalid UUID format" in result.output
        
        # Verify that unregister_agent was not called
        mock_client.unregister_agent.assert_not_called()
    
    def test_invalid_metadata(self, runner, mock_client):
        """Test CLI handling of invalid metadata."""
        # Test with invalid JSON format
        result = runner.invoke(cli, ["memory", "remember", "test content", "--agent-id", TEST_AGENT["id"], "--metadata", "{invalid"], catch_exceptions=True)
        assert "Invalid JSON format" in result.output
        assert result.exit_code != 0

        # Test with non-object JSON
        result = runner.invoke(cli, ["memory", "remember", "test content", "--agent-id", TEST_AGENT["id"], "--metadata", '"string"'], catch_exceptions=True)
        assert "Metadata must be a JSON object" in result.output
        assert result.exit_code != 0
    
    def test_invalid_relationship_type(self, runner):
        """Test handling of invalid relationship types."""
        result = runner.invoke(cli, [
            "memory", "link",
            TEST_MEMORY_EDGE["source_memory"],
            TEST_MEMORY_EDGE["target_memory"],
            "--relationship", "invalid-type"
        ])
        assert result.exit_code != 0
        assert "Invalid relationship type" in result.output
    
    def test_invalid_weight(self, runner):
        """Test handling of invalid weights."""
        result = runner.invoke(cli, [
            "memory", "link",
            TEST_MEMORY_EDGE["source_memory"],
            TEST_MEMORY_EDGE["target_memory"],
            "--relationship", "related_to",
            "--weight", "2.0"
        ])
        assert result.exit_code != 0
        assert "Weight must be between 0.0 and 1.0" in result.output 