# Agent as MCP Server (Microsoft Agent Framework)

This repo demonstrates how to **expose an agent as an MCP server** using the **Microsoft Agent Framework (MAF)**, and how to connect to it from:
- a **test ping client** (`mcp-ping.py`), and
- a **ChatAgent orchestration client** (`client-local-mcp.py`) that uses the local MCP server as a tool.

It uses the **STDIO transport** for MCP, which means the client launches the server as a subprocess and the two sides exchange JSON‑RPC messages over **stdin/stdout**.

> **Files**
>
> - `agent-as-mcp-svr.py` — MCP **server** that exposes the agent via `agent.as_mcp_server()` and `stdio_server()`.
> - `mcp-ping.py` — Minimal **client** that launches the server with `stdio_client()`, lists tools, and calls the agent tool.
> - `client-local-mcp.py` — **ChatAgent** orchestration example using `MCPStdioTool` to connect to the local server.
>

---

## Prerequisites

- Python 3.10+
- Recommended: a virtual environment
- Packages:
  ```bash
  pip install --pre agent-framework mcp anyio azure-identity python-dotenv
  ```

## Environment Configuration

If you use **Azure OpenAI** (recommended):
```bash
export AZURE_OPENAI_ENDPOINT="https://<your-endpoint>.cognitiveservices.azure.com/"
export AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME="gpt-4o"     # responses / agent usage
export AZURE_OPENAI_CHAT_DEPLOYMENT_NAME="gpt-4o"          # optional for chat client
export AZURE_OPENAI_API_VERSION="2025-03-01-preview"       # or 'preview'
# One of:
export AZURE_OPENAI_API_KEY="<your-key>"                   # simplest
# OR AAD-based:
# (unset REQUESTS_CA_BUNDLE SSL_CERT_FILE; az login)
# export AZURE_USE_CLI=1
```

> Corporate CA bundle users: ensure `REQUESTS_CA_BUNDLE` (and optionally `SSL_CERT_FILE`) point to a **valid** PEM path. For `az login`, you may need to temporarily unset those vars.

## How to Run

### 1) Quick local ping (STDIO client/server)
This starts the server as a subprocess and calls the agent tool:

```bash
python mcp-ping.py
```

Expected output (abridged):
```
TOOLS: ['RestaurantAgent']
== RestaurantAgent input schema ==
{ ... JSON schema ... }

== Health Check (JSON) ==
{ "status": "ok", "endpoint": "...", ... }
```

### 2) Orchestrated ChatAgent using the MCP server
This lets a ChatAgent use the local MCP server as a tool:
```bash
python client-local-mcp.py
```

It will run a sequence of prompts (health check, menu list, dietary filter, pricing, happy hour).

## Troubleshooting

- **Invalid JSON / EOF** when running the server alone — you launched the server without a client. Use `mcp-ping.py` (they start the server and speak MCP).
- **Token/credential errors** — provide `AZURE_OPENAI_API_KEY` or `AZURE_USE_CLI=1` with `az login`. For AAD chains, `DefaultAzureCredential` must be able to find an identity.
- **Tool arg mismatch** — the agent-as-tool typically expects a single `task` string. Ensure clients send `{"task":"your prompt"}`.

## How it Works (STDIO)

- **Server**: `stdio_server()` exposes async stdin/stdout streams; `server.run()` handles JSON‑RPC (initialize/list_tools/call_tool).
- **Client**: `stdio_client()` launches the server process and returns streams; `ClientSession` drives the JSON‑RPC calls.

See the annotated files for in‑line explanations of each step.

---
