# Verify the link_memories call
mock_client.link_memories.assert_called_once_with(
    source_memory_id=memories[1].id,
    target_memory_id=memories[0].id,
    relationship=EdgeType.PART_OF,
    weight=1.0,
    metadata=EdgeMetadata(
        relationship=EdgeType.PART_OF,
        weight=1.0,
        bidirectional=True,
        additional={
            "document_sequence": True,
            "sequence_index": 1
        }
    )
) 