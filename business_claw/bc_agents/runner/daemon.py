# -*- coding: utf-8 -*-
"""
Business Claw - Agent Runner Daemon

Main daemon that polls Frappe for tasks and executes them via LLM.
"""

import frappe
import json
import time
import threading
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .task_poller import TaskPoller
from .llm_router import LLMRouter
from .mcp_client import get_mcp_client
from .hitl_handler import HITLHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentRunnerDaemon")


class AgentRunnerDaemon:
    """
    Main daemon for executing AI tasks.

    Polls Frappe for pending tasks, routes to Claude API with MCP tools,
    and supports HITL workflow for write actions.
    """

    MAX_ITERATIONS = 5
    POLL_INTERVAL = 5

    _instance = None
    _running = False
    _thread = None

    def __new__(cls):
        """Singleton pattern for daemon."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize daemon components."""
        if self._initialized:
            return

        self.task_poller = TaskPoller()
        self.hitl_handler = HITLHandler()
        self.mcp_client = get_mcp_client()
        self._running = False
        self._initialized = True

        logger.info("AgentRunnerDaemon initialized")

    @classmethod
    def start(cls) -> bool:
        """
        Start the daemon in a background thread.

        Returns:
            True if started successfully
        """
        if cls._running:
            logger.warning("Daemon is already running")
            return False

        cls._running = True
        cls._thread = threading.Thread(target=cls._run_loop, daemon=True)
        cls._thread.start()

        logger.info("AgentRunnerDaemon started")
        return True

    @classmethod
    def stop(cls) -> bool:
        """
        Stop the daemon.

        Returns:
            True if stopped successfully
        """
        if not cls._running:
            logger.warning("Daemon is not running")
            return False

        cls._running = False

        if cls._thread:
            cls._thread.join(timeout=10)

        logger.info("AgentRunnerDaemon stopped")
        return True

    @classmethod
    def _run_loop(cls):
        """Main daemon loop."""
        while cls._running:
            try:
                cls._process_cycle()
            except Exception as e:
                logger.error(f"Error in process cycle: {str(e)}")
                frappe.log_error(
                    f"Daemon process cycle error: {str(e)}", "Agent Runner Daemon"
                )

            time.sleep(cls.POLL_INTERVAL)

    @classmethod
    def _process_cycle(cls):
        """Process one polling cycle."""
        instance = cls()

        tasks = instance.task_poller.fetch_pending_tasks(limit=5)

        if not tasks:
            return

        logger.info(f"Processing {len(tasks)} pending tasks")

        for task in tasks:
            if not cls._running:
                break

            try:
                cls._execute_task(task)
            except Exception as e:
                logger.error(f"Task execution error for {task['name']}: {str(e)}")
                instance.task_poller.mark_failed(task["name"], str(e))

    @classmethod
    def _execute_task(cls, task: Dict):
        """
        Execute a single task.

        Args:
            task: Task dictionary from poller
        """
        instance = cls()
        task_name = task["name"]
        agent_name = task["assigned_agent"]

        if not agent_name:
            logger.error(f"Task {task_name} has no assigned agent")
            instance.task_poller.mark_failed(task_name, "No agent assigned")
            return

        router = LLMRouter(agent_name)

        if not router.check_token_budget():
            logger.warning(f"Agent {agent_name} exceeded token budget")
            return

        instance.task_poller.mark_processing(task_name)

        try:
            task_input = cls._build_task_input(task)
            mcp_tools = cls._format_tools_for_claude()

            result = router.execute_task(
                task_input=task_input,
                mcp_tools=mcp_tools,
                context_callback=lambda: cls._get_task_context(task_name),
            )

            instance._handle_execution_result(task_name, agent_name, result)

        except Exception as e:
            logger.error(f"Task execution failed: {str(e)}")
            instance.task_poller.mark_failed(task_name, str(e))

    @classmethod
    def _build_task_input(cls, task: Dict) -> str:
        """
        Build task input for LLM.

        Args:
            task: Task dictionary

        Returns:
            Formatted task input string
        """
        parts = []

        if task.get("title"):
            parts.append(f"Task: {task['title']}")

        if task.get("description"):
            parts.append(f"\nDescription: {task['description']}")

        input_payload = task.get("input_payload", {})
        if input_payload:
            parts.append(
                f"\nInput Data:\n{json.dumps(input_payload, indent=2, default=str)}"
            )

        return "\n".join(parts)

    @classmethod
    def _format_tools_for_claude(cls) -> List[Dict]:
        """
        Get MCP tools formatted for Claude API.

        Returns:
            List of tool definitions in Claude format
        """
        instance = cls()

        try:
            tools = instance.mcp_client.list_tools()

            claude_tools = []
            for tool in tools:
                name = tool.get("name", "")
                description = tool.get("description", "")
                input_schema = tool.get("inputSchema", {})

                properties = {}
                required = []

                if "properties" in input_schema:
                    for prop_name, prop_def in input_schema["properties"].items():
                        properties[prop_name] = {
                            "type": prop_def.get("type", "string"),
                            "description": prop_def.get("description", ""),
                        }

                if "required" in input_schema:
                    required = input_schema["required"]

                claude_tools.append(
                    {
                        "name": name,
                        "description": description,
                        "input_schema": {
                            "type": "object",
                            "properties": properties,
                            "required": required,
                        },
                    }
                )

            return claude_tools

        except Exception as e:
            logger.error(f"Failed to get MCP tools: {str(e)}")
            return []

    @classmethod
    def _get_task_context(cls, task_name: str) -> Optional[Dict]:
        """
        Get additional context for a task.

        Args:
            task_name: Task name

        Returns:
            Context dictionary or None
        """
        try:
            task_detail = frappe.get_doc("AI Task", task_name)

            context = {
                "task_name": task_name,
                "priority": task_detail.priority,
                "parent_task": task_detail.parent_task,
                "iteration": task_detail.iteration_count or 0,
            }

            if task_detail.parent_task:
                parent = frappe.get_doc("AI Task", task_detail.parent_task)
                context["parent"] = {
                    "name": parent.name,
                    "title": parent.title,
                    "status": parent.status,
                }

            children = frappe.get_all(
                "AI Task",
                filters={"parent_task": task_name},
                fields=["name", "title", "status"],
            )
            if children:
                context["children"] = children

            return context

        except Exception as e:
            logger.error(f"Failed to get task context: {str(e)}")
            return None

    @classmethod
    def _handle_execution_result(cls, task_name: str, agent_name: str, result: Dict):
        """
        Handle task execution result.

        Args:
            task_name: Task name
            agent_name: Agent that executed the task
            result: Execution result from LLM router
        """
        instance = cls()

        output = result.get("output", "")
        iterations = result.get("iterations", 0)
        tokens_used = result.get("tokens_used", 0)

        instance.task_poller.update_iteration(task_name, tokens_used)

        if "needs_approval" in output.lower() or "awaiting" in output.lower():
            instance.hitl_handler.pause_for_approval(
                task_name=task_name,
                agent_name=agent_name,
                draft=output,
                action_type="create",
            )
            return

        instance.task_poller.mark_completed(
            task_name,
            {"output": output, "iterations": iterations, "tokens_used": tokens_used},
        )

    @classmethod
    def _check_token_budget(cls, agent_name: str) -> bool:
        """
        Check if agent has remaining token budget.

        Args:
            agent_name: Agent to check

        Returns:
            True if budget available
        """
        try:
            router = LLMRouter(agent_name)
            return router.check_token_budget()
        except Exception:
            return False

    @staticmethod
    def reset_daily_tokens():
        """
        Reset daily token usage for all active agents.

        Called by scheduler daily.
        """
        try:
            for agent in frappe.get_all("AI Agent", filters={"is_active": 1}):
                doc = frappe.get_doc("AI Agent", agent.name)
                doc.current_token_usage = 0
                doc.save(ignore_permissions=True)

            frappe.db.commit()
            logger.info("Daily token usage reset completed")

        except Exception as e:
            logger.error(f"Failed to reset daily tokens: {str(e)}")
            frappe.log_error(
                f"Daily token reset error: {str(e)}", "Agent Runner Daemon"
            )

    @classmethod
    def is_running(cls) -> bool:
        """Check if daemon is running."""
        return cls._running

    @classmethod
    def get_status(cls) -> Dict:
        """
        Get daemon status.

        Returns:
            Status dictionary
        """
        instance = cls()

        pending = instance.task_poller.fetch_pending_tasks(limit=100)
        awaiting = instance.hitl_handler.get_pending_approvals()

        return {
            "running": cls._running,
            "poll_interval": cls.POLL_INTERVAL,
            "max_iterations": cls.MAX_ITERATIONS,
            "pending_tasks": len(pending),
            "awaiting_approval": len(awaiting),
            "thread_alive": cls._thread.is_alive() if cls._thread else False,
        }
