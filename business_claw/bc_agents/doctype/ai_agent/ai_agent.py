# -*- coding: utf-8 -*-
import frappe
from frappe.model.document import Document
from datetime import datetime
import json


class AIAgent(Document):
    def validate(self):
        self.set_default_system_prompt()
        self.validate_parent_agent()

    def set_default_system_prompt(self):
        if not self.system_prompt:
            role_prompts = {
                "CEO": "You are the Chief Executive Officer agent. You provide strategic direction, make high-level decisions, and oversee all operations.",
                "COO": "You are the Chief Operating Officer agent. You optimize processes, ensure operational efficiency, and coordinate daily activities.",
                "CTO": "You are the Chief Technology Officer agent. You oversee technology decisions, system architecture, and technical strategy.",
                "CFO": "You are the Chief Financial Officer agent. You manage financial planning, accounting, and financial risk management.",
                "CMO": "You are the Chief Marketing Officer agent. You develop marketing strategies, brand positioning, and customer engagement.",
                "CSO": "You are the Chief Sales Officer agent. You drive sales strategy, manage sales teams, and optimize revenue generation.",
                "CIO": "You are the Chief Information Officer agent. You manage information systems, data strategy, and IT operations.",
                "VP Engineering": "You are a VP of Engineering agent. You lead technical teams, manage software development, and ensure code quality.",
                "VP Sales": "You are a VP of Sales agent. You manage sales operations, pipeline, and team performance.",
                "Product Manager": "You are a Product Manager agent. You define product vision, gather requirements, and coordinate development.",
                "Developer": "You are a Developer agent. You write code, implement features, and fix bugs following best practices.",
                "QA Engineer": "You are a QA Engineer agent. You test software, identify bugs, and ensure quality standards.",
                "DevOps Engineer": "You are a DevOps Engineer agent. You manage infrastructure, deployment, and system operations.",
                "Data Analyst": "You are a Data Analyst agent. You analyze data, generate insights, and create reports.",
                "Customer Support": "You are a Customer Support agent. You help customers, resolve issues, and provide excellent service.",
            }

            default_prompt = role_prompts.get(
                self.agent_role, "You are an AI agent helping with business operations."
            )

            if self.agent_type == "orchestrator":
                default_prompt += " As an orchestrator, you coordinate multiple agents, delegate tasks, and ensure workflow completion."
            elif self.agent_type == "reviewer":
                default_prompt += " As a reviewer, you evaluate work quality, provide feedback, and ensure standards are met."
            elif self.agent_type == "worker":
                default_prompt += " As a worker, you execute assigned tasks efficiently and report progress."
            elif self.agent_type == "analyst":
                default_prompt += " As an analyst, you research, gather information, and provide data-driven insights."

            self.system_prompt = json.dumps(
                {"role": "system", "content": default_prompt}, indent=2
            )

    def validate_parent_agent(self):
        if self.parent_agent and self.parent_agent == self.name:
            frappe.throw("An agent cannot be its own parent.")

    def get_mcp_scope(self):
        if self.mcp_scope:
            try:
                return (
                    json.loads(self.mcp_scope)
                    if isinstance(self.mcp_scope, str)
                    else self.mcp_scope
                )
            except json.JSONDecodeError:
                return {}
        return {}

    def update_token_usage(self, tokens_used):
        self.current_token_usage = (self.current_token_usage or 0) + tokens_used
        self.save(ignore_permissions=True)

    def mark_idle(self):
        self.status = "Idle"
        self.last_active = datetime.now()
        self.save(ignore_permissions=True)

    def mark_working(self):
        self.status = "Working"
        self.last_active = datetime.now()
        self.save(ignore_permissions=True)

    def mark_error(self, error_message=None):
        self.status = "Error"
        self.last_active = datetime.now()
        if error_message:
            frappe.log_error(f"AI Agent Error: {self.name}", error_message)
        self.save(ignore_permissions=True)


def reset_daily_token_usage():
    for agent in frappe.get_all("AI Agent", filters={"is_active": 1}):
        doc = frappe.get_doc("AI Agent", agent.name)
        doc.current_token_usage = 0
        doc.save(ignore_permissions=True)

    frappe.db.commit()
