##########################################################################################
# Annotated file: client-local-mcp.py
# Purpose: This file is annotated with explanatory comments for clarity when publishing to GitHub.
# NOTE: No executable code has been changed—only comments were added.
#
# Key ideas covered in these annotations:
# - What the file does in the overall MCP + Microsoft Agent Framework (MAF) architecture.
# - How STDIO client/server works for MCP (JSON-RPC over stdin/stdout).
# - Where authentication, environment variables, and model settings are used.
# - How tools and agents are composed and exposed to clients like VS Code Copilot Agents.
##########################################################################################

# client_local_mcp.py
# Drive a local MCP stdio server from a ChatAgent using Microsoft Agent Framework.
# Updated to exercise: health_check, list_menu, find_by_diet, get_item_price (with currency), happy_hour_specials.

import os
import sys
import asyncio
from dotenv import load_dotenv

from agent_framework import ChatAgent, MCPStdioTool
# MAF AZURE CHAT CLIENT: Bridges to Azure OpenAI 'Chat' API for conversational agents.
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.openai import OpenAIChatClient

# Azure Identity: DefaultAzureCredential (env/MSI/VSCode/etc.) or AzureCliCredential for token acquisition.
from azure.identity import AzureCliCredential, DefaultAzureCredential

load_dotenv(override=False)

# Function definition below:
def make_chat_client():
    """
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
    Prefer Azure OpenAI if AZURE_OPENAI_ENDPOINT is set; otherwise use OpenAI.
# Azure Identity: DefaultAzureCredential (env/MSI/VSCode/etc.) or AzureCliCredential for token acquisition.
    Azure auth order: API key -> Azure CLI (AZURE_USE_CLI=1) -> DefaultAzureCredential.
    """
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if azure_endpoint:
        deployment = (
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
            os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
            or os.getenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME")
        )
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
        api_version = os.getenv("AZURE_OPENAI_API_VERSION") or "preview"
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
        api_key = os.getenv("AZURE_OPENAI_API_KEY")

        credential = None
        if not api_key:
            if os.getenv("AZURE_USE_CLI") == "1":
# Azure Identity: DefaultAzureCredential (env/MSI/VSCode/etc.) or AzureCliCredential for token acquisition.
                credential = AzureCliCredential()
            else:
# Azure Identity: DefaultAzureCredential (env/MSI/VSCode/etc.) or AzureCliCredential for token acquisition.
                credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)

# MAF AZURE CHAT CLIENT: Bridges to Azure OpenAI 'Chat' API for conversational agents.
        return AzureOpenAIChatClient(
            endpoint=azure_endpoint,
            deployment_name=deployment,
            api_version=api_version,
            api_key=api_key,
            credential=credential,
        )

    # Fallback: public OpenAI (expects OPENAI_API_KEY)
    return OpenAIChatClient()

# main(): Entry point that runs the async supervisor with AnyIO.
async def main():
    """
    Connects to the local MCP server (stdio) and lets a ChatAgent use it as a tool.
    Your server exposes one MCP tool: 'RestaurantAgent' with input schema { task: string }.
    """
    chat_client = make_chat_client()

    # Launch your local MCP server (adjust filename if needed)
# MCPStdioTool: Wraps a local MCP stdio server as a tool the ChatAgent can invoke.
    mcp_tool = MCPStdioTool(
        name="restaurant",
        command="python",
        args=["agent-as-mcp-svr.py"],   # <--- make sure this matches your server filename
        description="Local RestaurantAgent MCP server over stdio",
# allowed_tools: Optional allowlist to restrict which tools from the MCP server are callable.
        allowed_tools=None,               # or ["RestaurantAgent"]
    )

    # Give the orchestrator clear instructions about how to call the MCP tool.
    # (The agent will translate natural prompts into {task: "..."} calls to the MCP server.)
    orchestrator_instructions = (
        "You can use the 'restaurant' MCP tool to talk to the RestaurantAgent. "
        "When invoking it, pass a single argument named 'task' containing the user request. "
        "The RestaurantAgent has internal tools:\n"
        "- health_check: quick diagnostics, returns JSON\n"
        "- list_menu [optional category]\n"
        "- find_by_diet [vegan|vegetarian|gluten-free]\n"
        "- get_item_price [item, optional currency]\n"
        "- happy_hour_specials [optional now_iso]\n"
        "Prefer concise answers for chat, and return raw JSON when the user explicitly asks for JSON."
    )

# ChatAgent: An orchestrator agent that can decide to use tools (including MCP tools) during reasoning.
    async with mcp_tool, ChatAgent(
        chat_client=chat_client,
        name="Orchestrator",
        instructions=orchestrator_instructions,
    ) as agent:

# Async function definition below:
        async def run_task(title: str, prompt: str):
            print(f"\n=== {title} ===")
            res = await agent.run(prompt, tools=mcp_tool)
            print(res)

        # 1) Health check (JSON desired)
        await run_task("Health Check", "Ask the RestaurantAgent to run a health check and return JSON.")

        # 2) Full menu (structured)
        await run_task("Full Menu JSON", "List the entire menu as JSON.")

        # 3) Category filter
        await run_task("Mains Only", "List menu items in the 'mains' category as JSON.")

        # 4) Dietary filter
        await run_task("Vegan Options", "Show vegan options as JSON.")

        # 5) FX pricing (currency)
        await run_task("Price in GBP", "What is the price of Grilled Tofu in GBP? Return a brief answer.")

        # 6) Happy hour dynamics (time-aware)
        await run_task("Happy Hour Specials", "Show happy-hour specials now, as JSON.")

        # 7) Fuzzy lookup + error handling
        await run_task("Fuzzy Lookup", "What is the price of 'biscuit' in USD? If not found, suggest closest items.")

        # 8) Casual small-talk (ensure the agent still replies naturally)
        await run_task("Small Talk", "How are you today?")

if __name__ == "__main__":
    asyncio.run(main())
