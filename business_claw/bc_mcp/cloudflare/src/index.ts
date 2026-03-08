/**
 * FrappeMCP - Cloudflare Workers Implementation
 * 
 * Remote MCP Server for ERPNext/Frappe
 * Deploy to Cloudflare Workers for global edge deployment
 */

import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { z } from "zod";

// Environment types
export interface Env {
  FRAPPE_URL: string;
  FRAPPE_API_KEY: string;
  FRAPPE_API_SECRET: string;
  CACHE: KVNamespace;
  AI: any;
  MCP_SESSION: DurableObjectNamespace;
}

// Tool input schemas
const GetDocumentSchema = z.object({
  doctype: z.string(),
  name: z.string(),
});

const CreateDocumentSchema = z.object({
  doctype: z.string(),
  data: z.record(z.any()),
  smart_mode: z.boolean().optional(),
});

const UpdateDocumentSchema = z.object({
  doctype: z.string(),
  name: z.string(),
  data: z.record(z.any()),
});

const ListDocumentsSchema = z.object({
  doctype: z.string(),
  filters: z.record(z.any()).optional(),
  fields: z.string().optional(),
  limit: z.number().optional(),
  order_by: z.string().optional(),
});

const SearchDocumentsSchema = z.object({
  doctype: z.string().optional(),
  query: z.string(),
  limit: z.number().optional(),
});

const GetDoctypeMetaSchema = z.object({
  doctype: z.string(),
});

// Frappe API Client
class FrappeClient {
  private baseUrl: string;
  private apiKey: string;
  private apiSecret: string;

  constructor(env: Env) {
    this.baseUrl = env.FRAPPE_URL || "https://frappe.example.com";
    this.apiKey = env.FRAPPE_API_KEY || "";
    this.apiSecret = env.FRAPPE_API_SECRET || "";
  }

  private getHeaders(): HeadersInit {
    return {
      "Content-Type": "application/json",
      "Authorization": `token ${this.apiKey}:${this.apiSecret}`,
    };
  }

  async getDocument(doctype: string, name: string) {
    const response = await fetch(
      `${this.baseUrl}/api/resource/${doctype}/${name}`,
      { headers: this.getHeaders() }
    );
    if (!response.ok) {
      throw new Error(`Failed to get document: ${response.statusText}`);
    }
    return response.json();
  }

  async createDocument(doctype: string, data: Record<string, any>) {
    const response = await fetch(
      `${this.baseUrl}/api/resource/${doctype}`,
      {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify(data),
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to create document: ${response.statusText}`);
    }
    return response.json();
  }

  async updateDocument(doctype: string, name: string, data: Record<string, any>) {
    const response = await fetch(
      `${this.baseUrl}/api/resource/${doctype}/${name}`,
      {
        method: "PUT",
        headers: this.getHeaders(),
        body: JSON.stringify(data),
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to update document: ${response.statusText}`);
    }
    return response.json();
  }

  async deleteDocument(doctype: string, name: string) {
    const response = await fetch(
      `${this.baseUrl}/api/resource/${doctype}/${name}`,
      {
        method: "DELETE",
        headers: this.getHeaders(),
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to delete document: ${response.statusText}`);
    }
    return { success: true };
  }

  async listDocuments(
    doctype: string,
    filters?: Record<string, any>,
    fields?: string,
    limit = 20,
    orderBy = "modified desc"
  ) {
    const params = new URLSearchParams();
    if (filters) params.set("filters", JSON.stringify(filters));
    if (fields) params.set("fields", fields);
    params.set("limit", String(limit));
    params.set("order_by", orderBy);

    const response = await fetch(
      `${this.baseUrl}/api/method/frappe.client.get_list?${params}`,
      { headers: this.getHeaders() }
    );
    if (!response.ok) {
      throw new Error(`Failed to list documents: ${response.statusText}`);
    }
    return response.json();
  }

  async searchDocuments(doctype: string, query: string, limit = 20) {
    const response = await fetch(
      `${this.baseUrl}/api/method/frappe.client.validate_and_search`,
      {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({ doctype, query, limit }),
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to search documents: ${response.statusText}`);
    }
    return response.json();
  }

  async getDoctypeMeta(doctype: string) {
    const response = await fetch(
      `${this.baseUrl}/api/method/frappe.model.meta.get_meta`,
      {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({ doctype }),
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to get doctype meta: ${response.statusText}`);
    }
    return response.json();
  }

  async getDoctypeFields(doctype: string) {
    const response = await fetch(
      `${this.baseUrl}/api/method/frappe.model.user_settings.get_for`,
      {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({ doctype }),
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to get doctype fields: ${response.statusText}`);
    }
    return response.json();
  }

  async submitDocument(doctype: string, name: string) {
    const response = await fetch(
      `${this.baseUrl}/api/method/frappe.client.submit`,
      {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({ doctype, name }),
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to submit document: ${response.statusText}`);
    }
    return response.json();
  }

  async cancelDocument(doctype: string, name: string) {
    const response = await fetch(
      `${this.baseUrl}/api/method/frappe.client.cancel`,
      {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({ doctype, name }),
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to cancel document: ${response.statusText}`);
    }
    return response.json();
  }
}

// Create MCP Server
function createMcpServer() {
  const server = new McpServer({
    name: "FrappeMCP",
    version: "1.0.0",
  });

  // List available tools
  server.tool(
    "list_tools",
    "List all available MCP tools",
    {},
    async () => {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              [
                "get_document",
                "create_document",
                "update_document",
                "delete_document",
                "list_documents",
                "search_documents",
                "get_doctype_meta",
                "get_doctype_fields",
                "submit_document",
                "cancel_document",
              ],
              null,
              2
            ),
          },
        ],
      };
    }
  );

  // Get Document
  server.tool(
    "get_document",
    "Fetch a document by DocType and name",
    {
      doctype: z.string(),
      name: z.string(),
    },
    async ({ doctype, name }, env: Env) => {
      const client = new FrappeClient(env);
      const result = await client.getDocument(doctype, name);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    }
  );

  // Create Document
  server.tool(
    "create_document",
    "Create a new document",
    CreateDocumentSchema,
    async ({ doctype, data, smart_mode }, env: Env) => {
      const client = new FrappeClient(env);
      const result = await client.createDocument(doctype, data);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    }
  );

  // Update Document
  server.tool(
    "update_document",
    "Update an existing document",
    UpdateDocumentSchema,
    async ({ doctype, name, data }, env: Env) => {
      const client = new FrappeClient(env);
      const result = await client.updateDocument(doctype, name, data);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    }
  );

  // Delete Document
  server.tool(
    "delete_document",
    "Delete a document",
    {
      doctype: z.string(),
      name: z.string(),
    },
    async ({ doctype, name }, env: Env) => {
      const client = new FrappeClient(env);
      const result = await client.deleteDocument(doctype, name);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    }
  );

  // List Documents
  server.tool(
    "list_documents",
    "List documents with filters",
    ListDocumentsSchema,
    async ({ doctype, filters, fields, limit, order_by }, env: Env) => {
      const client = new FrappeClient(env);
      const result = await client.listDocuments(
        doctype,
        filters,
        fields,
        limit,
        order_by
      );
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    }
  );

  // Search Documents
  server.tool(
    "search_documents",
    "Search documents across DocTypes",
    SearchDocumentsSchema,
    async ({ doctype, query, limit }, env: Env) => {
      const client = new FrappeClient(env);
      const result = await client.searchDocuments(doctype || "", query, limit);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    }
  );

  // Get DocType Meta
  server.tool(
    "get_doctype_meta",
    "Get metadata for a DocType",
    GetDoctypeMetaSchema,
    async ({ doctype }, env: Env) => {
      const client = new FrappeClient(env);
      const result = await client.getDoctypeMeta(doctype);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    }
  );

  // Submit Document
  server.tool(
    "submit_document",
    "Submit a document",
    {
      doctype: z.string(),
      name: z.string(),
    },
    async ({ doctype, name }, env: Env) => {
      const client = new FrappeClient(env);
      const result = await client.submitDocument(doctype, name);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    }
  );

  // Cancel Document
  server.tool(
    "cancel_document",
    "Cancel a document",
    {
      doctype: z.string(),
      name: z.string(),
    },
    async ({ doctype, name }, env: Env) => {
      const client = new FrappeClient(env);
      const result = await client.cancelDocument(doctype, name);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    }
  );

  // Add a resource
  server.resource(
    "frappe-docs",
    "mcp://documentation",
    async (uri) => {
      return {
        contents: [
          {
            uri: uri.href,
            text: "FrappeMCP - ERPNext MCP Server Documentation",
          },
        ],
      };
    }
  );

  return server;
}

// Export for Cloudflare Workers
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    // SSE endpoint for MCP
    if (url.pathname === "/sse" || url.pathname === "/sse/") {
      const transport = new SSEServerTransport("/messages", ctx);
      
      ctx.waitUntil(
        (async () => {
          await transport.start();
          const server = createMcpServer();
          await server.run(transport);
        })()
      );

      return transport.response();
    }

    // Messages endpoint
    if (url.pathname === "/messages" || url.pathname === "/messages/") {
      return new Response("Method not allowed", { status: 405 });
    }

    // Health check
    if (url.pathname === "/health" || url.pathname === "/") {
      return new Response(
        JSON.stringify({
          status: "healthy",
          service: "FrappeMCP",
          version: "1.0.0",
        }),
        {
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    return new Response("Not found", { status: 404 });
  },
};
