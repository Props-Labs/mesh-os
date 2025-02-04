# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.8] - 2025-02-04

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