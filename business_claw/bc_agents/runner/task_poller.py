# -*- coding: utf-8 -*-
"""
Business Claw - Task Poller

Polls Frappe for pending AI tasks and manages task lifecycle.
"""

import frappe
import json
from typing import Any, Dict, List, Optional
from frappe.utils import now_datetime


class TaskPoller:
    """
    Polls Frappe for pending tasks and manages their status.

    Handles fetching, status updates, and task lifecycle management.
    """

    def __init__(self):
        """Initialize Task Poller."""
        pass

    def fetch_pending_tasks(
        self, agent_name: str = None, limit: int = 10
    ) -> List[Dict]:
        """
        Fetch pending tasks ready for processing.

        Args:
            agent_name: Optional agent filter
            limit: Maximum number of tasks to fetch

        Returns:
            List of pending task dictionaries
        """
        filters = {"status": ["in", ["Pending", "Delegated"]]}

        if agent_name:
            filters["assigned_agent"] = agent_name

        tasks = frappe.get_all(
            "AI Task",
            filters=filters,
            fields=[
                "name",
                "title",
                "description",
                "assigned_agent",
                "priority",
                "due_date",
                "input_payload",
                "parent_task",
                "iteration_count",
            ],
            order_by="priority desc, creation asc",
            limit=limit,
        )

        return [self._parse_task(t) for t in tasks]

    def fetch_task_detail(self, task_name: str) -> Dict:
        """
        Fetch full task details.

        Args:
            task_name: Task name/ID

        Returns:
            Task document as dictionary
        """
        task = frappe.get_doc("AI Task", task_name)
        return {
            "name": task.name,
            "title": task.title,
            "description": task.description,
            "assigned_agent": task.assigned_agent,
            "status": task.status,
            "priority": task.priority,
            "input_payload": task.input_payload,
            "result_payload": task.result_payload,
            "error_message": task.error_message,
            "iteration_count": task.iteration_count or 0,
            "tokens_consumed": task.tokens_consumed or 0,
            "parent_task": task.parent_task,
            "agent_draft_output": task.agent_draft_output,
            "final_action_payload": task.final_action_payload,
        }

    def mark_processing(self, task_name: str) -> None:
        """
        Mark task as processing.

        Args:
            task_name: Task name/ID
        """
        task = frappe.get_doc("AI Task", task_name)
        task.mark_processing()
        frappe.db.commit()

    def mark_completed(self, task_name: str, result: Any) -> None:
        """
        Mark task as completed with result.

        Args:
            task_name: Task name/ID
            result: Task result (dict or string)
        """
        task = frappe.get_doc("AI Task", task_name)
        task.mark_completed(result)
        frappe.db.commit()

    def mark_failed(self, task_name: str, error: str) -> None:
        """
        Mark task as failed with error.

        Args:
            task_name: Task name/ID
            error: Error message
        """
        task = frappe.get_doc("AI Task", task_name)
        task.mark_failed(error)
        frappe.db.commit()

    def mark_awaiting_approval(self, task_name: str, draft: str, action: str) -> None:
        """
        Mark task as awaiting user approval.

        Args:
            task_name: Task name/ID
            draft: Draft output/action to approve
            action: Action type (e.g., "create", "update", "delete")
        """
        task = frappe.get_doc("AI Task", task_name)

        action_payload = {"action_type": action, "draft": draft}

        task.mark_awaiting_approval(draft, action_payload)
        frappe.db.commit()

    def update_iteration(self, task_name: str, tokens: int = 0) -> None:
        """
        Update task iteration count and token usage.

        Args:
            task_name: Task name/ID
            tokens: Tokens consumed in this iteration
        """
        task = frappe.get_doc("AI Task", task_name)
        task.iteration_count = (task.iteration_count or 0) + 1
        task.tokens_consumed = (task.tokens_consumed or 0) + tokens
        task.save(ignore_permissions=True)
        frappe.db.commit()

    def get_agent_tasks(self, agent_name: str, status: str = None) -> List[Dict]:
        """
        Get all tasks for an agent.

        Args:
            agent_name: Agent name
            status: Optional status filter

        Returns:
            List of task dictionaries
        """
        filters = {"assigned_agent": agent_name}
        if status:
            filters["status"] = status

        tasks = frappe.get_all(
            "AI Task",
            filters=filters,
            fields=[
                "name",
                "title",
                "status",
                "priority",
                "creation",
                "due_date",
                "iteration_count",
            ],
            order_by="priority desc, creation asc",
        )

        return tasks

    def _parse_task(self, task: Dict) -> Dict:
        """
        Parse task data for processing.

        Args:
            task: Raw task dictionary

        Returns:
            Parsed task with JSON payload
        """
        input_payload = task.get("input_payload", "{}")

        if isinstance(input_payload, str):
            try:
                input_payload = json.loads(input_payload)
            except json.JSONDecodeError:
                input_payload = {"raw": input_payload}

        return {**task, "input_payload": input_payload}
