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


def mark_done(task_id):
    """Manually mark a task as done."""
    tasks = load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            old_status = task["status"]
            if old_status == "done":
                log(f"Task {task_id} is already done.")
                return
            task["status"] = "done"
            save_tasks(tasks)
            log(f"MARKED DONE: {task_id} (was '{old_status}')")
            ready = get_ready_tasks(tasks)
            if ready:
                log("  Now ready to dispatch:")
                for r in ready:
                    log(f"    - {r['id']}: {r['title']}")
            return
    log(f"ERROR: Task '{task_id}' not found in tasks.yaml")
    sys.exit(1)


def add_task(task_id, title, agent, area, depends_on=None):
    """Add a new task to tasks.yaml."""
    tasks = load_tasks()
    if any(t["id"] == task_id for t in tasks):
        log(f"ERROR: Task '{task_id}' already exists.")
        sys.exit(1)
    if agent not in AGENT_MAP:
        log(f"ERROR: Agent must be one of {list(AGENT_MAP.keys())}")
        sys.exit(1)
    try:
        area_int = int(area)
    except (TypeError, ValueError):
        log(f"ERROR: Area must be an integer, got {area!r}")
        sys.exit(1)
    new_task = {
        "id": task_id,
        "title": title,
        "agent": agent,
        "area": area_int,
        "status": "pending",
        "description": f"TODO: Fill in description for {title}\n",
        "acceptance": ["TODO: Add acceptance criteria"],
        "custom_agent": "",
    }
    if depends_on:
        new_task["depends_on"] = depends_on
    tasks.append(new_task)
    save_tasks(tasks)
    log(f"ADDED: {task_id} — {title}")


def dispatch_ready_tasks():
    """Main dispatch loop."""
    tasks = load_tasks()
    ready = get_ready_tasks(tasks)

    if not ready:
        dispatched = [t for t in tasks if t["status"] == "dispatched"]
        pending = [t for t in tasks if t["status"] == "pending"]
        done = [t for t in tasks if t["status"] == "done"]
        log(f"No tasks ready to dispatch. "
            f"({len(done)} done, {len(dispatched)} dispatched, {len(pending)} pending/blocked)")
        if dispatched:
            log("  TIP: Run 'status' to check dispatched tasks, "
                "or 'mark-done <id>' to manually complete one.")
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
    """Check dispatched tasks for completion by inspecting issue state."""
    tasks = load_tasks()
    changed = False
    for task in tasks:
        if task["status"] != "dispatched":
            continue
        issue_num = task.get("issue_number")
        if not issue_num:
            log(f"  SKIP: {task['id']} has no issue_number")
            continue

        # Check if the GitHub issue is closed
        result = subprocess.run(
            ["gh", "issue", "view", str(issue_num),
             "--repo", REPO,
             "--json", "state,stateReason,title"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            log(f"  ERROR: Could not fetch issue #{issue_num}: {result.stderr.strip()}")
            continue

        issue_data = json.loads(result.stdout)
        state = issue_data.get("state", "")
        reason = issue_data.get("stateReason", "")

        if state == "CLOSED" and reason == "COMPLETED":
            task["status"] = "done"
            changed = True
            log(f"  DONE: {task['id']} (issue #{issue_num} closed as completed)")
        elif state == "CLOSED":
            log(f"  WARN: {task['id']} issue #{issue_num} closed as '{reason}' — not marking done")
        else:
            log(f"  OPEN: {task['id']} issue #{issue_num} still open")

    if changed:
        save_tasks(tasks)
        log("Tasks updated.")
    else:
        log("No status changes detected.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dispatch"
    if cmd == "dispatch":
        dispatch_ready_tasks()
    elif cmd == "status":
        check_status()
    elif cmd == "ready":
        tasks = load_tasks()
        ready = get_ready_tasks(tasks)
        if ready:
            for t in ready:
                print(f"  READY: {t['id']}: {t['title']}")
        else:
            print("  No tasks ready. Run 'status' or 'mark-done <id>' first.")
    elif cmd == "mark-done":
        if len(sys.argv) < 3:
            print("Usage: manager.py mark-done <task-id>")
            sys.exit(1)
        mark_done(sys.argv[2])
    elif cmd == "add-task":
        if len(sys.argv) < 6:
            print("Usage: manager.py add-task <id> <title> <agent> <area> [depends_on]")
            sys.exit(1)
        add_task(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5],
                 sys.argv[6] if len(sys.argv) > 6 else None)
    else:
        print("Usage: manager.py <command> [args]")
        print("Commands:")
        print("  dispatch                  Dispatch ready tasks to agents")
        print("  status                    Check dispatched tasks for completion")
        print("  ready                     List tasks ready to dispatch")
        print("  mark-done <task-id>       Manually mark a task as done")
        print("  add-task <id> <title> <agent> <area> [depends_on]")