##########################################################################################
# Annotated file: mcp-ping.py
# Purpose: This file is annotated with explanatory comments for clarity when publishing to GitHub.
# NOTE: No executable code has been changed—only comments were added.
#
# Key ideas covered in these annotations:
# - What the file does in the overall MCP + Microsoft Agent Framework (MAF) architecture.
# - How STDIO client/server works for MCP (JSON-RPC over stdin/stdout).
# - Where authentication, environment variables, and model settings are used.
# - How tools and agents are composed and exposed to clients like VS Code Copilot Agents.
##########################################################################################

# mcp-ping.py
# Ping the local MCP stdio server (agent_as_mcp_azure.py) and call the RestaurantAgent tool.

import anyio
# MCP CLIENT SESSION: ClientSession wraps the JSON-RPC dialogue (initialize, list_tools, call_tool).
from mcp.client.session import ClientSession
# MCP CLIENT: stdio_client spawns a subprocess and connects over its stdin/stdout; StdioServerParameters
#               defines how to launch the server command and args.
from mcp.client.stdio import StdioServerParameters, stdio_client

SERVER_CMD = "python"
SERVER_ARGS = ["agent-as-mcp-svr.py"]  # <-- make sure this matches your server filename

# Function definition below:
def _extract_tools(result):
    # Support multiple SDK return shapes
    if hasattr(result, "tools"):
        return result.tools
    if isinstance(result, tuple):
        return result[0]
    return result

# Async function definition below:
async def _safe_initialize(session: ClientSession):
    # Handle SDKs with different initialize() signatures
    for sig in (
        dict(client_name="mcp-ping", client_version="0.2.0"),
        dict(name="mcp-ping", version="0.2.0"),
        dict(),
    ):
        try:
# initialize(): JSON-RPC handshake with the MCP server; versions differ on arg names.
            await session.initialize(**sig)
            return
        except TypeError:
            continue
# initialize(): JSON-RPC handshake with the MCP server; versions differ on arg names.
    await session.initialize()

# Function definition below:
def _print_response(title, result):
    print(f"\n== {title} ==")
    for item in getattr(result, "content", []) or []:
        print(getattr(item, "text", str(item)))

# main(): Entry point that runs the async supervisor with AnyIO.
async def main():
    params = StdioServerParameters(command=SERVER_CMD, args=SERVER_ARGS)
# stdio_client(): Launches the server process and returns (read, write) streams for JSON-RPC.
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await _safe_initialize(session)

            # Discover tools
# list_tools(): Discover the list of tools exposed by the MCP server.
            lt = await session.list_tools()
            tools = _extract_tools(lt)
            names = [getattr(t, "name", getattr(t, "id", "<unnamed>")) for t in tools]
            print("TOOLS:", names)

            # Find the agent tool (RestaurantAgent)
            tool = None
            for t in tools:
                n = getattr(t, "name", getattr(t, "id", ""))
                if n:
                    tool = t
                    break
            if not tool:
                raise RuntimeError("No tools discovered from server")

            tool_name = getattr(tool, "name", getattr(tool, "id", "RestaurantAgent"))
            schema = getattr(tool, "inputSchema", getattr(tool, "input_schema", {}))
            print(f"\n== {tool_name} input schema ==\n{schema}")

            # Calls aligned to the latest server features (expects {task: "<prompt>"}):
            tests = [
                ("Health Check (JSON)", "Run health_check and return JSON."),
                ("Full Menu (JSON)", "List the entire menu as JSON."),
                ("Category = mains (JSON)", "List menu items in the 'mains' category as JSON."),
                ("Diet = vegan (JSON)", "Show vegan options as JSON."),
                ("Price in GBP", "What is the price of Grilled Tofu in GBP? Return a brief answer."),
                ("Happy Hour (JSON)", "Show happy-hour specials now, as JSON."),
                ("Fuzzy Lookup", "What is the price of 'biscuit' in USD? If not found, suggest closest items."),
                ("Small Talk", "How are you today?"),
            ]

            for title, task in tests:
# call_tool(): Invoke a tool by name with structured arguments and await the result.
                res = await session.call_tool(tool_name, {"task": task})
                _print_response(title, res)

if __name__ == "__main__":
    anyio.run(main)
