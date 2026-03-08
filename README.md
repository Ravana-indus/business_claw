# Business Claw

An ERPNext app with MCP (Model Context Protocol) integration for Ravana Industries.

## Features

### MCP Server
- AI-powered MCP server for ERPNext
- Integration with Frappe/ERPNext APIs
- Cloudflare deployment support

### Checklist System (bc_checklist)
A comprehensive checklist system for business operations.

#### DocTypes
- **Checklist Template** - Master templates for checklists
- **Checklist Template Item** - Individual steps in a template
- **Checklist Run** - Active checklist instances
- **Checklist Run Item** - Step items in a run

#### Features
- 30 pre-built templates covering:
  - HR & People Operations
  - Finance & Compliance
  - Legal & Risk Management
  - Operations & Delivery
  - Sales & Marketing
  - Technology & Systems
  - Strategic & Management
- Automatic template item copying
- Assignee, Due Date, Attachment, and Remarks for each step
- Workflow-based approval process

### bc_audit
- AI action logging
- Approval request tracking

### bc_guardrails
- Approval gates
- Policy enforcement
- Risk scoring
- Denylist management

## Installation

```bash
# Install the app
bench get-app business_claw
bench --site [site-name] install-app business_claw

# Run migrations
bench --site [site-name] migrate
```

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start bench
bench start
```

### Cloudflare Deployment
```bash
cd business_claw/bc_mcp/cloudflare
npm install
wrangler deploy
```

## Templates Included

The checklist system includes 30 templates organized by department:

- **HR**: Hiring, Onboarding, Exit, Leave, Performance
- **Finance**: Payment, Refund, Expense, Tax
- **Legal**: Contracts, Complaints, Privacy
- **Operations**: Service Delivery, Quality Control
- **Marketing**: Campaigns, Influencers, Content
- **IT**: System Release, Access Management
- **Strategic**: Partnerships, Expansion

## License

MIT License
