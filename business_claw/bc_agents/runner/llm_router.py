# -*- coding: utf-8 -*-
"""
Business Claw - LLM Router

Routes tasks to Claude API with MCP tools support.
"""

import frappe
import json
from typing import Any, Dict, List, Optional, Callable
from anthropic import Anthropic


class LLMRouter:
    """
    Routes tasks to Claude API with tool use support.

    Manages agent configuration, executes tasks with MCP tools,
    and tracks token usage.
    """

    def __init__(self, agent_name: str):
        """
        Initialize LLM Router for an agent.

        Args:
            agent_name: Name of the AI Agent to use
        """
        self.agent_name = agent_name
        self.agent = self._load_agent()
        self.client = self._create_anthropic_client()
        self.model = self.agent.claude_model or "claude-sonnet-4-20250514"
        self.max_tokens = self.agent.max_tokens or 4096

    def _load_agent(self) -> Any:
        """Load agent configuration from Frappe."""
        try:
            return frappe.get_doc("AI Agent", self.agent_name)
        except Exception as e:
            frappe.throw(f"Failed to load agent {self.agent_name}: {str(e)}")

    def _create_anthropic_client(self) -> Anthropic:
        """Create Anthropic client with API key from site config."""
        api_key = frappe.conf.get("anthropic_api_key")
        if not api_key:
            frappe.throw("anthropic_api_key not configured in site_config.json")
        return Anthropic(api_key=api_key)

    def execute_task(
        self, task_input: str, mcp_tools: List[Dict], context_callback: Callable = None
    ) -> Dict:
        """
        Execute a task using Claude with MCP tools.

        Args:
            task_input: Task description/instructions
            mcp_tools: List of MCP tool definitions
            context_callback: Optional callback to get additional context

        Returns:
            Dict with output, tokens_used, iterations
        """
        system_prompt = self._get_system_prompt()
        messages = self._build_messages(task_input, context_callback)

        tokens_used = 0
        iterations = 0
        all_content = []
        max_iterations = 5

        while iterations < max_iterations:
            iterations += 1

            response = self._send_message(
                messages=messages, system=system_prompt, tools=mcp_tools
            )

            tokens_used += response.usage.input_tokens + response.usage.output_tokens

            assistant_content = response.content
            all_content.extend(assistant_content)

            messages.append({"role": "assistant", "content": assistant_content})

            if not self._has_tool_calls(assistant_content):
                break

            tool_results = self._process_tool_calls(assistant_content)

            for tool_result in tool_results:
                messages.append(tool_result)

        output = self._extract_text_output(all_content)
        self._update_token_usage(tokens_used)

        return {
            "output": output,
            "tokens_used": tokens_used,
            "iterations": iterations,
            "tool_calls_made": sum(
                1 for c in all_content if hasattr(c, "type") and c.type == "tool_use"
            ),
        }

    def _get_system_prompt(self) -> str:
        """Get system prompt from agent config."""
        system_prompt = self.agent.system_prompt

        if isinstance(system_prompt, str):
            try:
                parsed = json.loads(system_prompt)
                return parsed.get("content", "")
            except json.JSONDecodeError:
                return system_prompt

        return system_prompt or "You are an AI agent helping with business operations."

    def _build_messages(
        self, task_input: str, context_callback: Callable
    ) -> List[Dict]:
        """Build message history for the conversation."""
        messages = []

        if context_callback:
            context = context_callback()
            if context:
                messages.append(
                    {
                        "role": "user",
                        "content": f"Context:\n{json.dumps(context, indent=2)}",
                    }
                )

        messages.append({"role": "user", "content": task_input})

        return messages

    def _send_message(
        self, messages: List[Dict], system: str, tools: List[Dict]
    ) -> Any:
        """Send message to Claude API."""
        return self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
            tools=tools,
        )

    def _has_tool_calls(self, content: List) -> bool:
        """Check if response contains tool calls."""
        return any(hasattr(c, "type") and c.type == "tool_use" for c in content)

    def _process_tool_calls(self, content: List) -> List[Dict]:
        """
        Process tool calls and return results.

        Args:
            content: Assistant message content with tool calls

        Returns:
            List of tool result messages
        """
        from .mcp_client import get_mcp_client

        results = []
        mcp_client = get_mcp_client()

        for block in content:
            if hasattr(block, "type") and block.type == "tool_use":
                tool_name = block.name
                tool_args = block.input

                try:
                    result = mcp_client.call_tool(tool_name, tool_args)
                    results.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(result, default=str),
                                }
                            ],
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(
                                        {"error": str(e)}, default=str
                                    ),
                                    "isError": True,
                                }
                            ],
                        }
                    )

        return results

    def _extract_text_output(self, content: List) -> str:
        """Extract text output from response content."""
        text_parts = []

        for block in content:
            if hasattr(block, "type"):
                if block.type == "text":
                    text_parts.append(block.text)

        return "\n".join(text_parts) if text_parts else ""

    def _update_token_usage(self, tokens_used: int):
        """Update agent token usage in database."""
        try:
            self.agent.update_token_usage(tokens_used)
        except Exception as e:
            frappe.log_error(
                f"Failed to update token usage for {self.agent_name}: {str(e)}",
                "LLM Router",
            )

    def check_token_budget(self) -> bool:
        """
        Check if agent has remaining token budget.

        Returns:
            True if budget available, False otherwise
        """
        daily_limit = self.agent.daily_token_limit or 100000
        current_usage = self.agent.current_token_usage or 0

        return current_usage < daily_limit
