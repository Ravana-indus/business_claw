# -*- coding: utf-8 -*-
"""
Business Claw - Agent Runner Integration Tests
"""

import frappe
import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestAIAgentCreation(unittest.TestCase):
    """Tests for AI Agent creation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_agent_data = {
            "doctype": "AI Agent",
            "agent_name": "Test Agent",
            "agent_role": "Developer",
            "agent_type": "worker",
            "ai_provider": "Claude",
            "claude_model": "claude-sonnet-4-20250514",
            "is_active": 1,
            "max_tokens": 4096,
            "daily_token_limit": 100000,
        }

    def tearDown(self):
        """Clean up test data."""
        if frappe.db.exists("AI Agent", "Test Agent"):
            frappe.delete_doc("AI Agent", "Test Agent")
            frappe.db.commit()

    @patch("frappe.get_doc")
    def test_ai_agent_creation(self, mock_get_doc):
        """Test creating a new AI Agent document."""
        mock_doc = Mock()
        mock_doc.name = "Test Agent"
        mock_get_doc.return_value = mock_doc

        from bc_agents.doctype.ai_agent.ai_agent import AIAgent

        agent = AIAgent(self.test_agent_data)
        self.assertEqual(agent.agent_name, "Test Agent")
        self.assertEqual(agent.agent_role, "Developer")
        self.assertEqual(agent.agent_type, "worker")

    def test_agent_default_system_prompt(self):
        """Test that default system prompts are set correctly."""
        from bc_agents.doctype.ai_agent.ai_agent import AIAgent

        agent = AIAgent(self.test_agent_data)
        agent.set_default_system_prompt()

        self.assertIsNotNone(agent.system_prompt)
        prompt_data = json.loads(agent.system_prompt)
        self.assertEqual(prompt_data.get("role"), "system")
        self.assertIn("Developer", prompt_data.get("content", ""))

    def test_agent_system_prompt_for_orchestrator(self):
        """Test system prompt for orchestrator agent type."""
        self.test_agent_data["agent_type"] = "orchestrator"
        self.test_agent_data["agent_role"] = "CEO"

        from bc_agents.doctype.ai_agent.ai_agent import AIAgent

        agent = AIAgent(self.test_agent_data)
        agent.set_default_system_prompt()

        prompt_data = json.loads(agent.system_prompt)
        self.assertIn("orchestrator", prompt_data.get("content", "").lower())

    def test_agent_validation_rejects_self_parent(self):
        """Test that agent cannot be its own parent."""
        from bc_agents.doctype.ai_agent.ai_agent import AIAgent

        agent = AIAgent(self.test_agent_data)
        agent.name = "Test Agent"
        agent.parent_agent = "Test Agent"

        with self.assertRaises(frappe.ValidationError):
            agent.validate_parent_agent()


class TestAITaskCreation(unittest.TestCase):
    """Tests for AI Task creation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_task_data = {
            "doctype": "AI Task",
            "title": "Test Task",
            "description": "A test task for unit testing",
            "assigned_agent": "Test Agent",
            "status": "Pending",
            "priority": "Medium",
            "input_payload": '{"task": "test", "data": "sample"}',
        }

    @patch("frappe.get_doc")
    def test_ai_task_creation(self, mock_get_doc):
        """Test creating a new AI Task document."""
        mock_doc = Mock()
        mock_doc.name = "Test Task"
        mock_get_doc.return_value = mock_doc

        from bc_agents.doctype.ai_task.ai_task import AITask

        task = AITask(self.test_task_data)
        self.assertEqual(task.title, "Test Task")
        self.assertEqual(task.status, "Pending")
        self.assertEqual(task.priority, "Medium")

    def test_task_parse_input_payload(self):
        """Test parsing valid JSON input payload."""
        from bc_agents.doctype.ai_task.ai_task import AITask

        task = AITask(self.test_task_data)
        task.parse_input_payload()

        parsed = json.loads(task.input_payload)
        self.assertEqual(parsed.get("task"), "test")

    def test_task_rejects_invalid_json_payload(self):
        """Test that invalid JSON payload raises error."""
        self.test_task_data["input_payload"] = "invalid json {"

        from bc_agents.doctype.ai_task.ai_task import AITask

        task = AITask(self.test_task_data)

        with self.assertRaises(frappe.ValidationError):
            task.parse_input_payload()

    def test_task_mark_processing(self):
        """Test marking task as processing."""
        from bc_agents.doctype.ai_task.ai_task import AITask

        task = AITask(self.test_task_data)
        task.mark_processing()

        self.assertEqual(task.status, "Processing")
        self.assertEqual(task.iteration_count, 1)


class TestTaskStatusTransitions(unittest.TestCase):
    """Tests for task status transitions."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_task_data = {
            "doctype": "AI Task",
            "title": "Status Test Task",
            "status": "Pending",
        }

    def test_pending_to_processing(self):
        """Test transition from Pending to Processing."""
        from bc_agents.doctype.ai_task.ai_task import AITask

        task = AITask(self.test_task_data)
        task.mark_processing()

        self.assertEqual(task.status, "Processing")

    def test_processing_to_awaiting_approval(self):
        """Test transition from Processing to Awaiting Approval."""
        from bc_agents.doctype.ai_task.ai_task import AITask

        task = AITask(self.test_task_data)
        task.mark_awaiting_approval(
            draft="Test draft output",
            action_payload={"action": "create"},
        )

        self.assertEqual(task.status, "Awaiting Approval")
        self.assertEqual(task.agent_draft_output, "Test draft output")

    def test_awaiting_approval_to_completed(self):
        """Test approval transition."""
        from bc_agents.doctype.ai_task.ai_task import AITask

        task = AITask(self.test_task_data)
        task.mark_awaiting_approval("draft", {})
        task.approve()

        self.assertEqual(task.status, "Completed")
        self.assertIsNotNone(task.approved_on)

    def test_awaiting_approval_to_failed(self):
        """Test rejection transition."""
        from bc_agents.doctype.ai_task.ai_task import AITask

        task = AITask(self.test_task_data)
        task.mark_awaiting_approval("draft", {})
        task.reject("User rejected the task")

        self.assertEqual(task.status, "Failed")
        self.assertEqual(task.error_message, "User rejected the task")

    def test_mark_completed_with_result(self):
        """Test marking task completed with result."""
        from bc_agents.doctype.ai_task.ai_task import AITask

        task = AITask(self.test_task_data)
        result = {"output": "success", "data": [1, 2, 3]}
        task.mark_completed(result)

        self.assertEqual(task.status, "Completed")
        result_data = json.loads(task.result_payload)
        self.assertEqual(result_data.get("output"), "success")

    def test_mark_failed_with_error(self):
        """Test marking task as failed with error."""
        from bc_agents.doctype.ai_task.ai_task import AITask

        task = AITask(self.test_task_data)
        task.mark_failed("Connection timeout")

        self.assertEqual(task.status, "Failed")
        self.assertEqual(task.error_message, "Connection timeout")


class TestExecutionLogCreation(unittest.TestCase):
    """Tests for AI Execution Log functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_log_data = {
            "doctype": "AI Execution Log",
            "task_reference": "Test Task",
            "agent": "Test Agent",
            "action_type": "tool_call",
            "tool_name": "bc_tools/doc.read",
            "request_data": '{"doc_type": "Customer"}',
            "response_data": '{"status": "success"}',
            "tokens_used": 150,
            "execution_duration": 0.5,
            "status": "Success",
        }

    @patch("frappe.get_doc")
    def test_execution_log_creation(self, mock_get_doc):
        """Test creating an execution log entry."""
        mock_doc = Mock()
        mock_doc.name = "Test Log"
        mock_get_doc.return_value = mock_doc

        from bc_agents.doctype.ai_execution_log.ai_execution_log import AIExecutionLog

        log = AIExecutionLog(self.test_log_data)
        self.assertEqual(log.task_reference, "Test Task")
        self.assertEqual(log.action_type, "tool_call")
        self.assertEqual(log.tokens_used, 150)

    def test_execution_log_json_serialization(self):
        """Test that request/response data is properly serialized."""
        from bc_agents.doctype.ai_execution_log.ai_execution_log import AIExecutionLog

        log = AIExecutionLog(self.test_log_data)

        request = json.loads(log.request_data)
        self.assertEqual(request.get("doc_type"), "Customer")

        response = json.loads(log.response_data)
        self.assertEqual(response.get("status"), "success")


class TestMCPClientMock(unittest.TestCase):
    """Tests for MCP Client functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_response = {
            "jsonrpc": "2.0",
            "id": "test123",
            "result": {"content": [{"type": "text", "text": '{"status": "success"}'}]},
        }

    @patch("requests.post")
    def test_mcp_client_initialization(self, mock_post):
        """Test MCP client can be initialized."""
        from bc_agents.runner.mcp_client import MCPClient

        client = MCPClient(site_url="http://localhost:8000")
        self.assertEqual(client.site_url, "http://localhost:8000")

    @patch("requests.post")
    def test_mcp_client_call_tool(self, mock_post):
        """Test calling an MCP tool."""
        mock_response = Mock()
        mock_response.json.return_value = self.mock_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        from bc_agents.runner.mcp_client import MCPClient

        client = MCPClient()
        result = client.call_tool("bc_tools/doc.read", {"doc_type": "Customer"})

        self.assertEqual(result.get("status"), "success")

    @patch("requests.post")
    def test_mcp_client_list_tools(self, mock_post):
        """Test listing available MCP tools."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test",
            "result": {
                "tools": [
                    {"name": "bc_tools/doc.read"},
                    {"name": "bc_tools/workflow.execute"},
                ]
            },
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        from bc_agents.runner.mcp_client import MCPClient

        client = MCPClient()
        tools = client.list_tools()

        self.assertEqual(len(tools), 2)
        self.assertEqual(tools[0].get("name"), "bc_tools/doc.read")

    @patch("requests.post")
    def test_mcp_client_handles_error(self, mock_post):
        """Test MCP client handles errors properly."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test",
            "error": {"message": "Tool not found"},
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        from bc_agents.runner.mcp_client import MCPClient

        client = MCPClient()

        with self.assertRaises(Exception) as context:
            client.call_tool("nonexistent_tool", {})

        self.assertIn("MCP tool error", str(context.exception))


class TestLLMRouterInitialization(unittest.TestCase):
    """Tests for LLM Router initialization."""

    @patch("frappe.get_doc")
    @patch("frappe.conf.get")
    def test_llm_router_initialization(self, mock_conf, mock_get_doc):
        """Test LLM router can be initialized with agent config."""
        mock_agent = Mock()
        mock_agent.name = "Test Agent"
        mock_agent.claude_model = "claude-sonnet-4-20250514"
        mock_agent.max_tokens = 4096
        mock_agent.system_prompt = '{"role": "system", "content": "Test prompt"}'
        mock_agent.current_token_usage = 0
        mock_agent.daily_token_limit = 100000
        mock_get_doc.return_value = mock_agent
        mock_conf.return_value = "test-api-key"

        from bc_agents.runner.llm_router import LLMRouter

        with patch("bc_agents.runner.llm_router.Anthropic"):
            router = LLMRouter("Test Agent")

            self.assertEqual(router.agent_name, "Test Agent")
            self.assertEqual(router.model, "claude-sonnet-4-20250514")

    @patch("frappe.get_doc")
    def test_llm_router_get_system_prompt(self, mock_get_doc):
        """Test extracting system prompt from agent config."""
        mock_agent = Mock()
        mock_agent.system_prompt = (
            '{"role": "system", "content": "You are a helpful assistant"}'
        )
        mock_get_doc.return_value = mock_agent

        from bc_agents.runner.llm_router import LLMRouter

        with patch("bc_agents.runner.llm_router.Anthropic"):
            router = LLMRouter("Test Agent")
            prompt = router._get_system_prompt()

            self.assertEqual(prompt, "You are a helpful assistant")

    @patch("frappe.get_doc")
    def test_llm_router_check_token_budget(self, mock_get_doc):
        """Test token budget checking."""
        mock_agent = Mock()
        mock_agent.current_token_usage = 50000
        mock_agent.daily_token_limit = 100000
        mock_get_doc.return_value = mock_agent

        from bc_agents.runner.llm_router import LLMRouter

        with patch("bc_agents.runner.llm_router.Anthropic"):
            router = LLMRouter("Test Agent")

            self.assertTrue(router.check_token_budget())

            mock_agent.current_token_usage = 100001
            self.assertFalse(router.check_token_budget())


class TestTaskPollerFetch(unittest.TestCase):
    """Tests for Task Poller fetch functionality."""

    @patch("frappe.get_all")
    def test_task_poller_fetch_pending_tasks(self, mock_get_all):
        """Test fetching pending tasks."""
        mock_get_all.return_value = [
            {
                "name": "Task-001",
                "title": "Test Task 1",
                "status": "Pending",
                "priority": "High",
            },
            {
                "name": "Task-002",
                "title": "Test Task 2",
                "status": "Pending",
                "priority": "Medium",
            },
        ]

        from bc_agents.runner.task_poller import TaskPoller

        poller = TaskPoller()
        tasks = poller.fetch_pending_tasks(limit=10)

        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].get("name"), "Task-001")

    @patch("frappe.get_all")
    def test_task_poller_fetch_with_agent_filter(self, mock_get_all):
        """Test fetching tasks for specific agent."""
        mock_get_all.return_value = [
            {"name": "Task-001", "title": "Agent Task", "assigned_agent": "Test Agent"},
        ]

        from bc_agents.runner.task_poller import TaskPoller

        poller = TaskPoller()
        tasks = poller.fetch_pending_tasks(agent_name="Test Agent")

        self.assertEqual(len(tasks), 1)
        mock_get_all.assert_called_once()

    @patch("frappe.get_all")
    def test_task_poller_parse_task(self, mock_get_all):
        """Test parsing task with JSON payload."""
        mock_get_all.return_value = [
            {
                "name": "Task-001",
                "title": "JSON Task",
                "input_payload": '{"key": "value", "nested": {"data": 123}}',
            },
        ]

        from bc_agents.runner.task_poller import TaskPoller

        poller = TaskPoller()
        tasks = poller.fetch_pending_tasks()

        self.assertIsInstance(tasks[0].get("input_payload"), dict)
        self.assertEqual(tasks[0]["input_payload"].get("key"), "value")

    @patch("frappe.get_doc")
    def test_task_poller_fetch_task_detail(self, mock_get_doc):
        """Test fetching full task details."""
        mock_task = Mock()
        mock_task.name = "Task-001"
        mock_task.title = "Detailed Task"
        mock_task.description = "Full description"
        mock_task.assigned_agent = "Test Agent"
        mock_task.status = "Processing"
        mock_task.priority = "High"
        mock_task.input_payload = "{}"
        mock_task.result_payload = None
        mock_task.error_message = None
        mock_task.iteration_count = 2
        mock_task.tokens_consumed = 500
        mock_task.parent_task = None
        mock_task.agent_draft_output = None
        mock_task.final_action_payload = None
        mock_get_doc.return_value = mock_task

        from bc_agents.runner.task_poller import TaskPoller

        poller = TaskPoller()
        detail = poller.fetch_task_detail("Task-001")

        self.assertEqual(detail.get("name"), "Task-001")
        self.assertEqual(detail.get("iteration_count"), 2)


if __name__ == "__main__":
    unittest.main()
