# -*- coding: utf-8 -*-
"""
Business Claw - HITL Handler

Handles Human-in-the-Loop approval workflow for agent actions.
"""

import frappe
import json
from typing import Any, Dict, Optional
from datetime import datetime


class HITLHandler:
    """
    Handles Human-in-the-Loop approval workflow.

    Manages pausing execution for approval, handling approved/rejected
    actions, and logging approval decisions.
    """

    def __init__(self):
        """Initialize HITL Handler."""
        pass

    def pause_for_approval(
        self,
        task_name: str,
        agent_name: str,
        draft: Any,
        action_type: str,
        action_args: Dict = None,
    ) -> Dict:
        """
        Pause task execution and request approval.

        Args:
            task_name: Task to pause
            agent_name: Agent requesting approval
            draft: Draft action/output to review
            action_type: Type of action (create, update, delete)
            action_args: Action arguments for execution

        Returns:
            Approval request details
        """
        from ..doctype.ai_task.ai_task import get_children

        task = frappe.get_doc("AI Task", task_name)

        draft_str = (
            json.dumps(draft, indent=2, default=str)
            if isinstance(draft, dict)
            else str(draft)
        )

        action_payload = {
            "action_type": action_type,
            "arguments": action_args or {},
            "draft": draft,
        }

        task.mark_awaiting_approval(draft_str, action_payload)
        frappe.db.commit()

        frappe.publish_realtime(
            "hitl_approval_requested",
            {
                "task_name": task_name,
                "agent_name": agent_name,
                "action_type": action_type,
                "title": task.title,
            },
            after_commit=True,
        )

        return {
            "status": "awaiting_approval",
            "task_name": task_name,
            "draft": draft_str,
            "action_type": action_type,
        }

    def execute_approved_action(self, task_name: str) -> Dict:
        """
        Execute an approved action.

        Args:
            task_name: Task with approved action

        Returns:
            Execution result
        """
        task = frappe.get_doc("AI Task", task_name)

        if task.status != "Awaiting Approval":
            return {
                "success": False,
                "error": f"Task {task_name} is not awaiting approval (status: {task.status})",
            }

        if not task.final_action_payload:
            return {"success": False, "error": "No action payload found for execution"}

        try:
            action_payload = json.loads(task.final_action_payload)
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid action payload format"}

        action_type = action_payload.get("action_type")
        action_args = action_payload.get("arguments", {})

        if not action_type:
            return {"success": False, "error": "No action type specified"}

        try:
            result = self._execute_action(action_type, action_args)

            task.approve()
            task.mark_completed(result)
            frappe.db.commit()

            return {"success": True, "result": result, "task_name": task_name}

        except Exception as e:
            task.mark_failed(str(e))
            frappe.db.commit()

            return {"success": False, "error": str(e)}

    def _execute_action(self, action_type: str, action_args: Dict) -> Dict:
        """
        Execute the approved action.

        Args:
            action_type: Type of action
            action_args: Action arguments

        Returns:
            Action result
        """
        from ..bc_mcp.router import ToolRouter
        from ..bc_audit.logger import log_action

        tool_map = {
            "create": action_args.get("tool_name", "doc.create"),
            "update": action_args.get("tool_name", "doc.update"),
            "delete": action_args.get("tool_name", "doc.delete"),
            "submit": action_args.get("tool_name", "doc.submit"),
            "cancel": action_args.get("tool_name", "doc.cancel"),
        }

        tool_name = tool_map.get(action_type)
        if not tool_name:
            raise ValueError(f"Unknown action type: {action_type}")

        router = ToolRouter()
        result = router.execute_tool(
            tool_name=tool_name,
            arguments=action_args.get("arguments", action_args),
            user="AI Agent",
        )

        log_action(
            tool_name=tool_name,
            request_json=action_args,
            response_json=result,
            risk_level="medium",
            approval_required=True,
            reference_doctype=action_args.get("doctype"),
            reference_name=action_args.get("name"),
        )

        return result

    def get_pending_approvals(self) -> list:
        """
        Get all tasks awaiting approval.

        Returns:
            List of pending approval tasks
        """
        return frappe.get_all(
            "AI Task",
            filters={"status": "Awaiting Approval"},
            fields=[
                "name",
                "title",
                "assigned_agent",
                "agent_draft_output",
                "final_action_payload",
                "creation",
                "iteration_count",
            ],
            order_by="creation asc",
        )

    def reject_task(self, task_name: str, reason: str = None) -> None:
        """
        Reject an awaiting approval task.

        Args:
            task_name: Task to reject
            reason: Rejection reason
        """
        task = frappe.get_doc("AI Task", task_name)
        task.reject(reason or "Rejected by approver")
        frappe.db.commit()

        frappe.publish_realtime(
            "hitl_task_rejected",
            {"task_name": task_name, "reason": reason},
            after_commit=True,
        )
