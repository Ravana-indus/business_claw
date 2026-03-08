# -*- coding: utf-8 -*-
"""
Business Claw - Tools Module

This module contains all MCP tool implementations organized by category:
- system: Health and meta tools
- meta: DocType introspection tools
- doc: Document CRUD tools
- workflow: Workflow tools
- file: File operations
- crm: CRM tools
- sales: Sales tools
- finance: Finance tools
- stock: Stock tools
- project: Project tools
"""

from . import system, meta, doc, workflow, file

# Business tools are optional
try:
	from . import crm, sales, finance, stock, project
except ImportError:
	pass

__all__ = [
	"system",
	"meta",
	"doc",
	"workflow",
	"file"
]
