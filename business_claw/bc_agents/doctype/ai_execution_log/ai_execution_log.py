# -*- coding: utf-8 -*-
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
import json


class AIExecutionLog(Document):
    pass


@frappe.whitelist()
def log_action(
    task_reference=None,
    agent=None,
    action_type=None,
    tool_name=None,
    request_data=None,
    response_data=None,
    tokens_used=0,
    execution_duration=0.0,
    status="Success",
    error_message=None,
):
    log = frappe.get_doc(
        {
            "doctype": "AI Execution Log",
            "timestamp": now_datetime(),
            "task_reference": task_reference,
            "agent": agent,
            "action_type": action_type,
            "tool_name": tool_name,
            "request_data": json.dumps(request_data)
            if isinstance(request_data, dict)
            else request_data,
            "response_data": json.dumps(response_data)
            if isinstance(response_data, dict)
            else response_data,
            "tokens_used": tokens_used or 0,
            "execution_duration": execution_duration or 0.0,
            "status": status,
            "error_message": error_message,
        }
    )
    log.insert(ignore_permissions=True)
    return {"name": log.name, "status": "logged"}


@frappe.whitelist()
def get_task_logs(task_name, limit=100):
    logs = frappe.get_all(
        "AI Execution Log",
        filters={"task_reference": task_name},
        fields=[
            "name",
            "timestamp",
            "action_type",
            "tool_name",
            "status",
            "tokens_used",
            "execution_duration",
            "error_message",
        ],
        order_by="timestamp desc",
        limit=limit,
    )
    return logs


@frappe.whitelist()
def get_agent_logs(agent_name, limit=100):
    logs = frappe.get_all(
        "AI Execution Log",
        filters={"agent": agent_name},
        fields=[
            "name",
            "timestamp",
            "task_reference",
            "action_type",
            "tool_name",
            "status",
            "tokens_used",
            "execution_duration",
        ],
        order_by="timestamp desc",
        limit=limit,
    )
    return logs


@frappe.whitelist()
def get_execution_summary(task_name):
    logs = frappe.get_all(
        "AI Execution Log",
        filters={"task_reference": task_name},
        fields=["tokens_used", "execution_duration", "status", "action_type"],
    )

    if not logs:
        return {"total_tokens": 0, "total_duration": 0.0, "action_counts": {}}

    total_tokens = sum(log.get("tokens_used") or 0 for log in logs)
    total_duration = sum(log.get("execution_duration") or 0.0 for log in logs)
    action_counts = {}
    for log in logs:
        action = log.get("action_type") or "Unknown"
        action_counts[action] = action_counts.get(action, 0) + 1

    return {
        "total_tokens": total_tokens,
        "total_duration": round(total_duration, 3),
        "action_counts": action_counts,
        "log_count": len(logs),
    }
