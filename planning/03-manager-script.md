# 03 — Manager Script

## Purpose

The manager script is a deterministic Python script (not AI-powered) that:

1. Reads a task queue
2. Creates GitHub Issues with the right context
3. Assigns them to the best agent
4. Polls for PR completion
5. Logs results

It runs from your terminal in VS Code.

## Task Queue Format

`scripts/tasks.yaml`:

```yaml
tasks:
  - id: schema-001
    area: 1
    agent: claude
    title: "Implement SchemaStore.upsert_entity and get_entity"
    description: |
      Implement the SchemaStore class in schema/store.py with:
      - upsert_entity(entity: dict) -> UpsertResult
      - get_entity(id: str) -> Entity
      
      Use SQLite. Follow the Entity contract in contracts/schema_to_backend.yaml.
      Test with the entity_tree fixture.
    acceptance:
      - "pytest schema/tests/ passes"
      - "entity_tree fixture round-trips through upsert + get"
    custom_agent: schema-builder
    status: pending

  - id: schema-002
    area: 1
    agent: claude
    title: "Implement SchemaStore.query_region"
    depends_on: schema-001
    description: |
      Add query_region(bbox) to SchemaStore.
      Follow the EntityList contract in contracts/schema_to_backend.yaml.
    acceptance:
      - "pytest schema/tests/ passes"
      - "Returns entities within bounding box"
    custom_agent: schema-builder
    status: pending

  - id: backend-001
    area: 7
    agent: copilot
    title: "FastAPI skeleton with GET /scene/manifest"
    depends_on: schema-001
    description: |
      Create backend/main.py with FastAPI.
      Implement GET /scene/manifest per contracts/backend_to_viewer.yaml.
      In stub mode, return the scene_manifest fixture.
    acceptance:
      - "curl localhost:8000/scene/manifest returns valid JSON"
      - "Response matches SceneManifest contract"
    custom_agent: backend-builder
    status: pending
```

## Script: `scripts/manager.py`

```python
#!/usr/bin/env python3
"""
HomeModel Manager Script
Creates GitHub Issues and assigns to coding agents.
Requires: gh CLI authenticated, PyYAML installed.
"""

import subprocess
import json
import yaml
import sys
from pathlib import Path
from datetime import datetime

REPO = "ChrisJones79/homemodel"
BASE_BRANCH = "master"
TASKS_FILE = Path(__file__).parent / "tasks.yaml"
LOG_FILE = Path(__file__).parent / "manager.log"

AGENT_MAP = {
    "copilot": "copilot-swe-agent",
    "claude": "anthropic-code-agent",
    "codex": "openai-code-agent",
}


def load_tasks():
    with open(TASKS_FILE) as f:
        return yaml.safe_load(f)["tasks"]


def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        yaml.dump({"tasks": tasks}, f, default_flow_style=False)


def log(msg):
    timestamp = datetime.now().isoformat()
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_ready_tasks(tasks):
    """Return tasks whose dependencies are met."""
    done_ids = {t["id"] for t in tasks if t["status"] == "done"}
    ready = []
    for t in tasks:
        if t["status"] != "pending":
            continue
        deps = t.get("depends_on")
        if deps is None or deps in done_ids:
            ready.append(t)
    return ready


def create_issue(task):
    """Create a GitHub Issue and return its number."""
    body = task["description"].strip()
    body += "\n\n## Acceptance Criteria\n"
    for criterion in task.get("acceptance", []):
        body += f"- [ ] {criterion}\n"
    body += f"\n## Custom Agent: `{task.get('custom_agent', 'default')}`"

    result = subprocess.run(
        [
            "gh", "issue", "create",
            "--repo", REPO,
            "--title", task["title"],
            "--body", body,
            "--label", f"area-{task['area']}",
        ],
        capture_output=True, text=True
    )
    # gh returns the issue URL
    url = result.stdout.strip()
    number = url.split("/")[-1]
    return int(number)


def get_repo_and_bot_ids():
    """Fetch the repository node ID and a login→id map of assignable actors."""
    query = '''
    query {
      repository(owner: "ChrisJones79", name: "homemodel") {
        id
        suggestedActors(capabilities: [CAN_BE_ASSIGNED], first: 100) {
          nodes {
            login
            __typename
            ... on Bot { id }
            ... on User { id }
          }
        }
      }
    }
    '''
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log(f"  ✗ Failed to fetch repo/bot IDs: {result.stderr}")
        return None, {}
    data = json.loads(result.stdout)
    if "errors" in data:
        log(f"  ✗ GraphQL errors fetching repo/bot IDs: {data['errors']}")
        return None, {}
    repo_id = data["data"]["repository"]["id"]
    actors = data["data"]["repository"]["suggestedActors"]["nodes"]
    bot_map = {a["login"]: a["id"] for a in actors}
    return repo_id, bot_map


def get_issue_id(issue_number):
    """Fetch the GraphQL node ID for an issue number."""
    query = '''
    query($number: Int!) {
      repository(owner: "ChrisJones79", name: "homemodel") {
        issue(number: $number) {
          id
        }
      }
    }
    '''
    result = subprocess.run(
        [
            "gh", "api", "graphql",
            "-f", f"query={query}",
            "-F", f"number={issue_number}",
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log(f"  ✗ Failed to fetch issue ID: {result.stderr}")
        return None
    data = json.loads(result.stdout)
    if "errors" in data:
        log(f"  ✗ GraphQL errors fetching issue ID: {data['errors']}")
        return None
    return data["data"]["repository"]["issue"]["id"]


def assign_agent(issue_number, task):
    """Assign a coding agent to an issue via GraphQL."""
    repo_id, bot_map = get_repo_and_bot_ids()
    if not repo_id:
        return False

    issue_id = get_issue_id(issue_number)
    if not issue_id:
        return False

    agent_name = task["agent"]
    bot_id = bot_map.get(AGENT_MAP[agent_name])
    if not bot_id:
        log(f"  ⚠ Agent '{agent_name}' not found in suggestedActors. Available: {list(bot_map.keys())}")
        return False

    custom_agent = task.get("custom_agent", "")
    mutation = '''
    mutation($issueId: ID!, $botId: ID!, $repoId: ID!, $baseRef: String!, $customAgent: String!) {
      addAssigneesToAssignable(input: {
        assignableId: $issueId,
        assigneeIds: [$botId],
        agentAssignment: {
          targetRepositoryId: $repoId,
          baseRef: $baseRef,
          customInstructions: "",  # reserved for future per-task instructions
          customAgent: $customAgent,
          model: ""  # empty uses the agent's default model
        }
      }) {
        assignable {
          ... on Issue {
            id
            assignees(first: 10) {
              nodes { login }
            }
          }
        }
      }
    }
    '''
    result = subprocess.run(
        [
            "gh", "api", "graphql",
            "-f", f"query={mutation}",
            "-F", f"issueId={issue_id}",
            "-F", f"botId={bot_id}",
            "-F", f"repoId={repo_id}",
            "-F", f"baseRef={BASE_BRANCH}",
            "-F", f"customAgent={custom_agent}",
            "-H", "GraphQL-Features: issues_copilot_assignment_api_support,coding_agent_model_selection",
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log(f"  ✗ GraphQL assignment failed: {result.stderr}")
        return False

    data = json.loads(result.stdout)
    if "errors" in data:
        log(f"  ✗ GraphQL errors: {data['errors']}")
        return False

    log(f"  ✓ Agent assigned via GraphQL")
    return True


def dispatch_ready_tasks():
    """Main dispatch loop."""
    tasks = load_tasks()
    ready = get_ready_tasks(tasks)

    if not ready:
        log("No tasks ready to dispatch.")
        return

    for task in ready:
        log(f"Dispatching: {task['id']} — {task['title']}")
        issue_num = create_issue(task)
        task["issue_number"] = issue_num
        if assign_agent(issue_num, task):
            task["status"] = "dispatched"
            log(f"  → Issue #{issue_num} assigned to @{task['agent']}")
        else:
            log(f"  ⚠ Assignment failed for #{issue_num}; task left as pending for retry")

    save_tasks(tasks)


def check_status():
    """Check dispatched tasks for completed PRs."""
    tasks = load_tasks()
    for task in tasks:
        if task["status"] != "dispatched":
            continue
        issue_num = task.get("issue_number")
        if not issue_num:
            continue
        # Check if issue has a linked merged PR
        result = subprocess.run(
            [
                "gh", "pr", "list",
                "--repo", REPO,
                "--search", f"closes #{issue_num}",
                "--json", "number,state,mergedAt",
            ],
            capture_output=True, text=True
        )
        prs = json.loads(result.stdout)
        for pr in prs:
            if pr.get("mergedAt"):
                task["status"] = "done"
                log(f"DONE: {task['id']} (PR #{pr['number']} merged)")

    save_tasks(tasks)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dispatch"
    if cmd == "dispatch":
        dispatch_ready_tasks()
    elif cmd == "status":
        check_status()
    elif cmd == "ready":
        tasks = load_tasks()
        for t in get_ready_tasks(tasks):
            print(f"  {t['id']}: {t['title']}")
    else:
        print("Usage: manager.py [dispatch|status|ready]")
```

## Usage

```bash
# See what's ready to go
python scripts/manager.py ready

# Create issues and assign agents
python scripts/manager.py dispatch

# Check if dispatched tasks have merged PRs
python scripts/manager.py status
```

## Notes

- The `gh issue edit --add-assignee` approach for Claude/Codex may require
  the GraphQL API instead (see [[01-repo-setup]] Step 6). If the CLI method
  fails silently, switch to the GraphQL mutation. This is a known rough edge.
- The script is intentionally simple. Extend it only when you hit a real need.
- Task dependencies are single-parent only. That's enough for now.

### Update
I updated `manager.py`, reflected above, after getting the correct agent login ids.

I don't have it working correctly as tasks.yaml isn't updated after the task inside it was completed.

## Checkpoint

- [x] `scripts/manager.py` committed
- [ ] `scripts/tasks.yaml` has at least 3 starter tasks
- [x] `python scripts/manager.py ready` shows expected output
- [x] Labels `area-1` through `area-7` created on the repo

→ Next: [[04-skill-files]]
