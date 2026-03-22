# -*- coding: utf-8 -*-
"""
Business Claw - Agent Setup Module

Functions for initializing agents and workspaces.
"""

import frappe
import json
import os
from pathlib import Path


def setup_default_agents():
    """
    Load default agents from JSON fixture and create them in Frappe.

    Returns:
        dict: Result with created/updated agent counts
    """
    fixture_path = Path(__file__).parent / "fixtures" / "default_agents.json"

    if not fixture_path.exists():
        frappe.throw(f"Default agents fixture not found: {fixture_path}")

    with open(fixture_path, "r") as f:
        agents_data = json.load(f)

    created = 0
    updated = 0
    errors = []

    for agent_data in agents_data:
        try:
            agent_name = agent_data.get("name")

            if frappe.db.exists("AI Agent", agent_name):
                doc = frappe.get_doc("AI Agent", agent_name)
                for key, value in agent_data.items():
                    if key not in ("doctype", "name"):
                        doc.set(key, value)
                doc.save(ignore_permissions=True)
                updated += 1
            else:
                doc = frappe.get_doc(
                    {
                        "doctype": "AI Agent",
                        **{k: v for k, v in agent_data.items() if k != "doctype"},
                    }
                )
                doc.insert(ignore_permissions=True)
                created += 1

        except Exception as e:
            errors.append({"agent": agent_data.get("name"), "error": str(e)})

    frappe.db.commit()

    return {
        "status": "success",
        "created": created,
        "updated": updated,
        "errors": errors,
        "total": len(agents_data),
    }


def create_agent_workspace():
    """
    Create 'Agent Control Center' workspace with agent management tools.

    Returns:
        dict: Workspace creation result
    """
    workspace_name = "Agent Control Center"

    if frappe.db.exists("Workspace", workspace_name):
        return {
            "status": "skipped",
            "message": f"Workspace '{workspace_name}' already exists",
        }

    workspace = frappe.get_doc(
        {
            "doctype": "Workspace",
            "name": workspace_name,
            "icon": "agent",
            "indicator_color": "green",
            "title": "Agent Control Center",
            "public": 1,
        }
    )
    workspace.insert(ignore_permissions=True)

    links = [
        {"label": "AI Agents", "link_type": "DocType", "link_to": "AI Agent"},
        {"label": "AI Tasks", "link_type": "DocType", "link_to": "AI Task"},
        {
            "label": "Execution Logs",
            "link_type": "DocType",
            "link_to": "AI Execution Log",
        },
        {
            "label": "Agent Runner Status",
            "link_type": "Page",
            "link_to": "agent-runner",
        },
    ]

    for link in links:
        link_doc = frappe.get_doc(
            {
                "doctype": "Workspace Link",
                "parent": workspace.name,
                "parentfield": "links",
                "parenttype": "Workspace",
                **link,
            }
        )
        link_doc.insert(ignore_permissions=True)

    frappe.db.commit()

    return {"status": "success", "workspace": workspace_name, "links": len(links)}


@frappe.whitelist()
def initialize_bc_agents():
    """
    Whitelisted entry point to initialize Business Claw agents.

    Creates default agents and sets up the Agent Control Center workspace.

    Returns:
        dict: Initialization result with agent and workspace status
    """
    if not frappe.has_permission("AI Agent", "write"):
        frappe.throw("Insufficient permissions to initialize agents")

    agents_result = setup_default_agents()
    workspace_result = create_agent_workspace()

    return {
        "agents": agents_result,
        "workspace": workspace_result,
        "initialized": True,
    }


@frappe.whitelist()
def get_agent_status():
    """
    Get status of all AI agents.

    Returns:
        dict: Agent status information
    """
    agents = frappe.get_all(
        "AI Agent",
        fields=[
            "name",
            "agent_name",
            "agent_role",
            "status",
            "is_active",
            "current_token_usage",
            "daily_token_limit",
        ],
    )

    return {
        "total": len(agents),
        "active": sum(1 for a in agents if a.get("is_active")),
        "agents": agents,
    }


@frappe.whitelist()
def reset_agent_tokens():
    """
    Reset token usage for all active agents.

    Returns:
        dict: Reset result
    """
    if not frappe.has_permission("AI Agent", "write"):
        frappe.throw("Insufficient permissions")

    count = 0
    for agent in frappe.get_all("AI Agent", filters={"is_active": 1}):
        doc = frappe.get_doc("AI Agent", agent.name)
        doc.current_token_usage = 0
        doc.save(ignore_permissions=True)
        count += 1

    frappe.db.commit()

    return {"status": "success", "reset_count": count}
