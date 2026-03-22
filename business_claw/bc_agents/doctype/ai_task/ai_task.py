# -*- coding: utf-8 -*-
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from datetime import datetime
import json


class AITask(Document):
    def validate(self):
        self.validate_agent_active()
        self.parse_input_payload()

    def validate_agent_active(self):
        if self.assigned_agent:
            agent = frappe.get_doc("AI Agent", self.assigned_agent)
            if not agent.is_active:
                frappe.throw(
                    f"Agent '{self.assigned_agent}' is not active. Please select an active agent."
                )

    def parse_input_payload(self):
        if self.input_payload:
            try:
                if isinstance(self.input_payload, str):
                    json.loads(self.input_payload)
            except json.JSONDecodeError as e:
                frappe.throw(f"Invalid JSON in input_payload: {str(e)}")

    def mark_processing(self):
        self.status = "Processing"
        self.iteration_count = 1
        self.save(ignore_permissions=True)

    def mark_awaiting_approval(self, draft, action_payload):
        self.status = "Awaiting Approval"
        self.agent_draft_output = draft
        self.final_action_payload = (
            json.dumps(action_payload, indent=2)
            if isinstance(action_payload, dict)
            else action_payload
        )
        self.iteration_count = (self.iteration_count or 0) + 1
        self.save(ignore_permissions=True)

        frappe.publish_realtime(
            "task_awaiting_approval",
            {"task_name": self.name, "title": self.title, "status": self.status},
            after_commit=True,
        )

    def approve(self):
        self.status = "Completed"
        self.approved_by = frappe.session.user
        self.approved_on = now_datetime()
        self.save(ignore_permissions=True)

        frappe.publish_realtime(
            "task_approved",
            {
                "task_name": self.name,
                "title": self.title,
                "approved_by": self.approved_by,
                "approved_on": str(self.approved_on),
            },
            after_commit=True,
        )

    def reject(self, error_message=None):
        self.status = "Failed"
        self.error_message = error_message or "Rejected by user"
        self.approved_by = frappe.session.user
        self.approved_on = now_datetime()
        self.save(ignore_permissions=True)

        frappe.publish_realtime(
            "task_rejected",
            {
                "task_name": self.name,
                "title": self.title,
                "error_message": self.error_message,
                "rejected_by": self.approved_by,
            },
            after_commit=True,
        )

    def mark_completed(self, result):
        self.status = "Completed"
        self.result_payload = (
            json.dumps(result, indent=2) if isinstance(result, dict) else result
        )
        self.save(ignore_permissions=True)

        frappe.publish_realtime(
            "task_completed",
            {"task_name": self.name, "title": self.title, "status": self.status},
            after_commit=True,
        )

    def mark_failed(self, error):
        self.status = "Failed"
        self.error_message = str(error)
        self.save(ignore_permissions=True)

        frappe.publish_realtime(
            "task_failed",
            {
                "task_name": self.name,
                "title": self.title,
                "error_message": self.error_message,
            },
            after_commit=True,
        )

    def create_child_task(self, title, agent_name, input_data):
        child = frappe.get_doc(
            {
                "doctype": "AI Task",
                "title": title,
                "assigned_agent": agent_name,
                "parent_task": self.name,
                "status": "Pending",
                "priority": self.priority,
                "input_payload": json.dumps(input_data)
                if isinstance(input_data, dict)
                else input_data,
                "due_date": self.due_date,
            }
        )
        child.insert(ignore_permissions=True)
        return child


def get_children(self):
    return frappe.get_all(
        "AI Task",
        filters={"parent_task": self.name},
        fields=["name", "title", "status", "priority", "assigned_agent"],
    )


@frappe.whitelist()
def approve_task(task_name):
    task = frappe.get_doc("AI Task", task_name)
    task.approve()
    return {"status": "success", "message": "Task approved"}


@frappe.whitelist()
def reject_task(task_name, reason):
    task = frappe.get_doc("AI Task", task_name)
    task.reject(reason)
    return {"status": "success", "message": "Task rejected"}


@frappe.whitelist()
def start_task(task_name):
    task = frappe.get_doc("AI Task", task_name)
    task.mark_processing()
    return {"status": "success", "message": "Task started"}


@frappe.whitelist()
def bulk_update_status(task_names, status):
    for task_name in task_names:
        task = frappe.get_doc("AI Task", task_name)
        task.status = status
        task.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "success", "message": f"{len(task_names)} tasks updated"}


@frappe.whitelist()
def get_task_summary(task_name):
    task = frappe.get_doc("AI Task", task_name)
    return {
        "tokens_consumed": task.tokens_consumed,
        "execution_time": task.execution_time,
        "iteration_count": task.iteration_count,
        "priority": task.priority,
    }


def get_pending_tasks(agent_name=None, limit=10):
    filters = {"status": ["in", ["Pending", "Delegated"]]}
    if agent_name:
        filters["assigned_agent"] = agent_name

    return frappe.get_all(
        "AI Task",
        filters=filters,
        fields=[
            "name",
            "title",
            "description",
            "priority",
            "due_date",
            "input_payload",
        ],
        order_by="priority desc, creation asc",
        limit=limit,
    )


def get_task_stats():
    stats = {}
    for status in [
        "Pending",
        "Processing",
        "Awaiting Approval",
        "Delegated",
        "Completed",
        "Failed",
        "Cancelled",
    ]:
        count = frappe.db.count("AI Task", {"status": status})
        stats[status] = count
    return stats
