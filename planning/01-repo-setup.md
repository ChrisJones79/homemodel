# 01 — Repo Setup

## Prerequisites

- [x] GitHub account with Copilot Pro (confirmed)
- [x] VS Code installed (confirmed)
- [x] Git configured locally
- [x] GitHub CLI (`gh`) installed — needed for manager script

## Step 1: Create the Repo

```bash
mkdir homemodel && cd homemodel
git init
gh repo create homemodel --private --source=. --push
```

## Step 2: Directory Structure

```bash
mkdir -p .github/agents
mkdir -p contracts
mkdir -p schema terrain structures vegetation
mkdir -p viewer ingestion backend
mkdir -p tools fixtures
mkdir -p scripts  # manager script lives here
```

## Step 3: Copy Contract Files

Move your existing YAML files into `contracts/`:
- `schema_to_backend.yaml`
- `backend_to_viewer.yaml`
- `ingestion_to_schema.yaml`
- `viewer_to_webxr.yaml`
- `domains_to_schema.yaml`

## Step 4: Create `copilot-instructions.md`

This file goes at the repo root. All three agents (Copilot, Claude, Codex) read it.

```markdown
# HomeModel — Repository Instructions

## What This Project Is
A locally-hosted, LAN-accessible 3D navigable model of a house and
surrounding five-acre property. GPS coordinates and altitude are the
absolute positioning system.

## Architecture
- Hybrid model: structured data (JSON/SQLite) → build step → glTF → Three.js
- WebXR path for Valve Index VR
- Interface contracts in `contracts/` are the source of truth between areas
- Every datum tracks provenance and version

## Conventions
- Python 3.11+, FastAPI for backend
- Three.js for browser rendering
- SQLite for local data store
- All GPS coordinates use WGS84: {lat, lon, alt_m}
- Scene origin: lat 42.98743, lon -70.98709, alt_m 26.8
- `HOMEMODEL_MODE=stub` or `=real` toggles mock/live dependencies
- Individual trees are first-class entities

## Testing
- Every module must pass with `HOMEMODEL_MODE=stub`
- Test fixtures are in `fixtures/` and in the contract YAML files
- Run: `pytest --tb=short`

## What NOT To Do
- Do not hardcode file paths outside the project root
- Do not bypass the schema layer — all data goes through SchemaStore
- Do not merge geometry formats — always output glTF for the viewer
```

## Step 5: Enable Agents

On github.com:
- [x] Go to Settings → Copilot → Coding agent
- [x] Enable coding agent for the `homemodel` repo
- [x] Under Partner Agents, enable **Claude** and **Codex**

## Step 6: Verify Agent Access

```bash
gh api graphql -f query='
  query {
    repository(owner: "ChrisJones79", name: "homemodel") {
      suggestedActors(capabilities: [CAN_BE_ASSIGNED], first: 100) {
        nodes { login __typename }
      }
    }
  }
'
```
---
# Failure Overcame (needed HTTPS URL not HTTPS as I had no ssh key setup when I `gh auth login` )

Ok this failed. I ran through

{  
 "data": {  
   "repository": null  
 },  
 "errors": [  
   {  
     "type": "NOT_FOUND",  
     "path": [  
       "repository"  
     ],  
     "locations": [  
       {  
         "line": 3,  
         "column": 5  
       }  
     ],  
     "message": "Could not resolve to a Repository with the name 'ChrisJones79/homemodel'."  
   }  
 ]  
}  
gh: Could not resolve to a Repository with the name 'ChrisJones79/homemodel'.

> I assume there was no ?sync from my local dir to github as the following steps which populated the local dirs weren't done or commited yet. Now that they are, would I commit and push?

Yep, exactly. The repo exists on GitHub but is empty. Just:

```bash
git add .
git commit -m "Initial commit"
git push -u origin master
```

Then retry that GraphQL query to verify.

$ git add . git commit -m "Initial commit" git push -u origin master [master (root-commit) 453f5dd] Initial commit 6 files changed, 355 insertions(+) create mode 100644 contracts/backend_to_viewer.yaml create mode 100644 contracts/domains_to_schema.yaml create mode 100644 contracts/ingestion_to_schema.yaml create mode 100644 contracts/schema_to_backend.yaml create mode 100644 contracts/viewer_to_webxr.yaml create mode 100644 copilot-instructions.md fatal: 'origin' does not appear to be a git repository fatal: Could not read from remote repository. Please make sure you have the correct access rights and the repository exists.

Check your remotes:

```bash
git remote -v
```

Likely empty since the initial `gh repo create` failed to push. If so:

```bash
git remote add origin git@github.com:ChrisJones79/homemodel.git
git push -u origin master
```

(Use the HTTPS URL instead if you picked HTTPS during `gh auth login`.)

You don't have an SSH key registered with GitHub. Quickest fix — switch to HTTPS:

```bash
git remote set-url origin https://github.com/ChrisJones79/homemodel.git
git push -u origin master
```

Or if you want SSH long-term, check if you have a key first:

```bash
ls ~/.ssh/id_*.pub
```

The `--push` flag failed (no commits), and that apparently aborted the entire command — including the repo creation itself. Just create it now:

```bash
gh repo create homemodel --private --source=. --push
```

Since you now have a commit, it should work end-to-end this time.

$ gh repo create homemodel --private --source=. --push ✓ Created repository ChrisJones79/homemodel on GitHub  https://github.com/ChrisJones79/homemodel X Unable to add remote "origin"

Remote already exists from your earlier `git remote add`. Just push:

```bash
git push -u origin master
```

$ git push -u origin master Enumerating objects: 9, done. Counting objects: 100% (9/9), done. Delta compression using up to 20 threads Compressing objects: 100% (9/9), done. Writing objects: 100% (9/9), 6.07 KiB | 6.07 MiB/s, done. Total 9 (delta 0), reused 0 (delta 0), pack-reused 0 (from 0) To https://github.com/ChrisJones79/homemodel.git * [new branch]      master -> master branch 'master' set up to track 'origin/master'.

# You're all set. Now retry that GraphQL query to verify agent access.

---
You should see `copilot-swe-agent` in the results. Claude and Codex appear as assignable agents in the Issue UI.





## Step 7: VS Code Extensions

- [x] GitHub Copilot (already installed)
- [x] GitHub Copilot Chat
- [x] GitHub Pull Requests
- [x] Python (ms-python)
- [x] GitLens (optional, helpful for reviewing agent PRs)

## Step 8: GitHub MCP Server in VS Code

Add to your VS Code `settings.json` or `.vscode/mcp.json`:

```json
{
  "servers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "X-MCP-Toolsets": "default,copilot_spaces"
      }
    }
  }
}
```

This lets you access your Spaces from inside VS Code agent mode.

## Checkpoint

After completing all steps above:
- [x] Repo exists on GitHub with contract files
- [x] `copilot-instructions.md` committed to root
- [x] All three agents enabled
- [ ] VS Code connected with MCP server

→ Next: [[02-agent-config]]
