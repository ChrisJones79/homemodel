# HomeEnvironment — Master Plan

## Architecture Summary

You are the solo human. Three AI coding agents (Copilot, Claude, Codex) work in parallel on GitHub Issues, producing PRs you review and merge. A manager script orchestrates issue creation and agent assignment. Copilot Spaces provide persistent context per work area.

## Main Interface: VS Code

VS Code is your cockpit. It connects to:
- **GitHub Copilot** (inline suggestions + agent mode for interactive work)
- **Claude cloud agent** (autonomous background sessions via Copilot integration)
- **Codex cloud agent** (autonomous background sessions via Copilot integration)
- **GitHub MCP Server** (access Spaces context from within the editor)
- **Terminal** (run the manager script, Claude CLI for local work)

## The Loop

```
┌─────────────────────────────────────────────┐
│  YOU (VS Code + Copilot Space)              │
│  - Plan in Space chat                       │
│  - Run manager script                       │
│  - Review PRs                               │
│  - Merge                                    │
└──────┬──────────────┬──────────────┬────────┘
       │              │              │
  @copilot        @claude        @codex
       │              │              │
   Issue→PR       Issue→PR       Issue→PR
       │              │              │
       └──────────────┴──────────────┘
                      │
              CI validates (pytest, lint, contract checks)
```

## Documents in This Vault

| File | Purpose |
|------|---------|
| [[00-master-plan]] | This file. The root. |
| [[01-repo-setup]] | Step-by-step repo creation with checkboxes |
| [[02-agent-config]] | Enabling agents, Spaces, custom agent files |
| [[03-manager-script]] | The orchestrator script design |
| [[04-skill-files]] | Per-work-area skill file template and content |
| [[05-progress-log]] | Running log of what's done, what's next |

## Work Areas

| #   | Area                | First Task                            | Agent Suggestion |
| --- | ------------------- | ------------------------------------- | ---------------- |
| 0   | Interface Contracts | Already done (YAML files exist)       | —                |
| 1   | Schema & Data Store | SQLite + SchemaStore class            | @claude          |
| 2   | Terrain & Property  | Elevation grid from USGS              | @copilot         |
| 3   | Structure Modeling  | Wall/room extrusion from measurements | @claude          |
| 4   | Vegetation Catalog  | Tree entity CRUD + canopy shapes      | @codex           |
| 5   | 3D Viewer           | Three.js scene loader from glTF       | @copilot         |
| 6   | Ingestion Pipeline  | Measurement + image submission        | @claude          |
| 7   | Backend API         | FastAPI serving schema to viewer      | @copilot         |

## Restart Points

When resuming after a break, check:
1. [[05-progress-log]] — what's the current state?
2. Open PRs on GitHub — anything waiting for review?
3. Manager script logs — any failed tasks to re-queue?
