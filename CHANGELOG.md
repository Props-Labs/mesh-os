# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.11] - 2025-02-05

### Fixed
- Fixed timestamp handling in `search_memories` function to properly handle timezone conversions
- Added explicit timezone casting with `AT TIME ZONE 'UTC'` for all temporal comparisons
- Improved handling of `_is_null` operator for both `created_at` and `expires_at` filters

## [0.1.10] - 2025-02-05

### Added
- Memory expiration support:
  - New `expires_at` field for memories to set expiration timestamps
  - Optional `expires_at` parameter in `remember()` function
  - Memories without expiration default to NULL (never expire)
- Enhanced memory search capabilities:
  - Added support for temporal filtering with standard Hasura operators (_gt, _gte, _lt, _lte, _eq)
  - Filter memories by `created_at` using `created_at_filter`
  - Filter memories by `expires_at` using `expires_at_filter`
  - All temporal filters are optional and can be combined with existing filters

### Changed
- Updated `search_memories` function to support temporal filtering
- Extended memory schema with `expires_at` field
- Improved GraphQL queries to include `expires_at` in responses
- Updated Memory class to include optional `expires_at` field

## [0.1.9] - 2025-02-05

### Added
- Automatic content chunking for large memories
  - Content exceeding 8192 tokens is automatically split into chunks
  - Chunks are linked with `follows_up` relationships
  - Each chunk includes metadata about its position and total chunks
  - Seamless handling of both single and multi-chunk memories
- Enhanced metadata filtering support in `search_memories`:
  - Exact value matching for numeric fields in metadata
  - Nested object matching in metadata
  - Array containment operations with `_contains` operator
  - Full support for deep nested metadata structures
- Improved IDE support and type hints:
  - Added `py.typed` marker for better type checking
  - Enhanced docstrings with examples and detailed descriptions
  - Added proper type hints for all public APIs
  - Better package metadata for development tools

### Changed
- `remember` function now returns either a single Memory or List[Memory] depending on chunking
- Enhanced memory metadata to support chunk information and relationships
- Enhanced package structure for better IDE integration
- Improved import organization in core modules

## [0.1.8] - 2025-02-05

### Added
- Agent status management
  - New `update_agent_status` function to update agent status
  - New CLI command `agent update-status <identifier> <status>` to change agent status
  - Supported statuses: active, inactive, error
  - Status updates work with both UUID and slug identifiers

### Changed
- Enhanced agent status validation in CLI to prevent invalid status values
- Improved error messages for agent status operations

## [0.1.7] - 2025-02-04

### Added
- Human-readable slugs for agent identification
  - Slugs must match pattern `^[a-z][a-z0-9_-]*[a-z0-9]$` (e.g., "my-agent-1")
  - New `get_agent_by_slug` function to retrieve agents by slug
  - Optional `slug` parameter in `register_agent` function
  - CLI commands now support agent lookup by slug

### Changed
- Agent registration now returns existing agent if slug is already in use
- CLI commands display agent slugs in output messages for easier reference
- Improved error messages for invalid slug formats

### Fixed
- Better error handling when using invalid slugs in API calls
- Clarified metadata filtering behavior in GraphQL queries
- Improved documentation for metadata filtering examples
 