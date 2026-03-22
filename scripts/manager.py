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
TASKS_FILE = Path(__file__).parent / "tasks.yaml"
LOG_FILE = Path(__file__).parent / "manager.log"

AGENT_MAP = {
    "copilot": "Copilot",
    "claude": "claude-by-anthropic",
    "codex": "Codex",
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


def assign_agent(issue_number, agent_name):
    """Assign the agent to the issue."""
    agent_login = AGENT_MAP[agent_name]
    subprocess.run(
        [
            "gh", "issue", "edit", str(issue_number),
            "--repo", REPO,
            "--add-assignee", agent_login,
        ],
        capture_output=True, text=True
    )


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
        assign_agent(issue_num, task["agent"])
        task["status"] = "dispatched"
        task["issue_number"] = issue_num
        log(f"  → Issue #{issue_num} assigned to @{task['agent']}")

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