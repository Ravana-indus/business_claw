# -*- coding: utf-8 -*-
"""
Business Claw - Agent Runner API

REST API endpoints for task management and agent control.
"""

import frappe
import json
from typing import Dict, List, Any, Optional
from frappe import _


@frappe.whitelist()
def create_task_for_agent(
    agent: str,
    title: str,
    description: str = None,
    input_data: Dict = None,
    priority: int = 0,
    due_date: str = None,
) -> Dict:
    """
    Create a new task for an agent.

    Args:
        agent: Agent name
        title: Task title
        description: Task description
        input_data: Input data dictionary
        priority: Priority (0-10, higher = more important)
        due_date: Due date string

    Returns:
        Created task info
    """
    if not frappe.db.exists("AI Agent", agent):
        frappe.throw(f"Agent '{agent}' does not exist")

    task = frappe.get_doc(
        {
            "doctype": "AI Task",
            "title": title,
            "description": description,
            "assigned_agent": agent,
            "priority": priority,
            "due_date": due_date,
            "input_payload": json.dumps(input_data) if input_data else "{}",
            "status": "Pending",
        }
    )

    task.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "task_name": task.name,
        "message": f"Task created for agent {agent}",
    }


@frappe.whitelist()
def approve_task(task: str) -> Dict:
    """
    Approve a task awaiting HITL approval.

    Args:
        task: Task name to approve

    Returns:
        Approval result
    """
    from .runner.hitl_handler import HITLHandler

    task_doc = frappe.get_doc("AI Task", task)

    if task_doc.status != "Awaiting Approval":
        frappe.throw(f"Task is not awaiting approval (status: {task_doc.status})")

    handler = HITLHandler()
    result = handler.execute_approved_action(task)

    return result


@frappe.whitelist()
def reject_task(task: str, reason: str = None) -> Dict:
    """
    Reject a task awaiting HITL approval.

    Args:
        task: Task name to reject
        reason: Rejection reason

    Returns:
        Rejection result
    """
    from .runner.hitl_handler import HITLHandler

    task_doc = frappe.get_doc("AI Task", task)

    if task_doc.status != "Awaiting Approval":
        frappe.throw(f"Task is not awaiting approval (status: {task_doc.status})")

    handler = HITLHandler()
    handler.reject_task(task, reason)

    return {"status": "success", "message": "Task rejected"}


@frappe.whitelist()
def get_agent_status(agent: str = None) -> List[Dict]:
    """
    Get status of agents.

    Args:
        agent: Optional agent filter

    Returns:
        List of agent status dictionaries
    """
    filters = {"is_active": 1}
    if agent:
        filters["name"] = agent

    agents = frappe.get_all(
        "AI Agent",
        filters=filters,
        fields=[
            "name",
            "agent_role",
            "agent_type",
            "status",
            "current_token_usage",
            "daily_token_limit",
            "last_active",
            "is_active",
        ],
    )

    for agent_doc in agents:
        task_stats = frappe.db.sql(
            """
            SELECT status, COUNT(*) as count
            FROM `tabAI Task`
            WHERE assigned_agent = %s
            GROUP BY status
        """,
            (agent_doc["name"],),
            as_dict=True,
        )

        agent_doc["task_stats"] = {stat["status"]: stat["count"] for stat in task_stats}

    return agents


@frappe.whitelist()
def get_pending_approvals() -> List[Dict]:
    """
    Get all tasks awaiting approval.

    Returns:
        List of pending approval tasks
    """
    from .runner.hitl_handler import HITLHandler

    handler = HITLHandler()
    return handler.get_pending_approvals()


@frappe.whitelist()
def get_task_tree(task: str) -> Dict:
    """
    Get task with its children.

    Args:
        task: Task name

    Returns:
        Task dictionary with children
    """
    task_doc = frappe.get_doc("AI Task", task)

    result = {
        "name": task_doc.name,
        "title": task_doc.title,
        "description": task_doc.description,
        "status": task_doc.status,
        "assigned_agent": task_doc.assigned_agent,
        "priority": task_doc.priority,
        "input_payload": task_doc.input_payload,
        "result_payload": task_doc.result_payload,
        "error_message": task_doc.error_message,
        "iteration_count": task_doc.iteration_count,
        "tokens_consumed": task_doc.tokens_consumed,
        "creation": str(task_doc.creation),
        "modified": str(task_doc.modified),
    }

    children = frappe.get_all(
        "AI Task",
        filters={"parent_task": task},
        fields=["name", "title", "status", "priority", "assigned_agent"],
    )

    if children:
        result["children"] = children

    return result


@frappe.whitelist()
def get_daemon_status() -> Dict:
    """
    Get the daemon status.

    Returns:
        Daemon status dictionary
    """
    from .runner.daemon import AgentRunnerDaemon

    return AgentRunnerDaemon.get_status()


@frappe.whitelist()
def start_daemon() -> Dict:
    """
    Start the agent runner daemon.

    Returns:
        Start result
    """
    from .runner.daemon import AgentRunnerDaemon

    success = AgentRunnerDaemon.start()

    return {
        "status": "success" if success else "failed",
        "message": "Daemon started" if success else "Daemon already running",
    }


@frappe.whitelist()
def stop_daemon() -> Dict:
    """
    Stop the agent runner daemon.

    Returns:
        Stop result
    """
    from .runner.daemon import AgentRunnerDaemon

    success = AgentRunnerDaemon.stop()

    return {
        "status": "success" if success else "failed",
        "message": "Daemon stopped" if success else "Daemon not running",
    }


@frappe.whitelist()
def get_task_history(task: str, limit: int = 20) -> List[Dict]:
    """
    Get task execution history.

    Args:
        task: Task name
        limit: Maximum records

    Returns:
        List of action logs for the task
    """
    from ..bc_audit.logger import get_document_history

    return get_document_history("AI Task", task, limit)


@frappe.whitelist()
def list_agents(role: str = None, type: str = None, is_active: int = 1) -> List[Dict]:
    """
    List agents with optional filters.

    Args:
        role: Agent role filter
        type: Agent type filter
        is_active: Active filter

    Returns:
        List of agent dictionaries
    """
    filters = {"is_active": is_active}

    if role:
        filters["agent_role"] = role
    if type:
        filters["agent_type"] = type

    return frappe.get_all(
        "AI Agent",
        filters=filters,
        fields=[
            "name",
            "agent_role",
            "agent_type",
            "status",
            "current_token_usage",
            "daily_token_limit",
            "last_active",
        ],
    )
