##########################################################################################
# Annotated file: agent-as-mcp-svr.py
# Purpose: This file is annotated with explanatory comments for clarity when publishing to GitHub.
# NOTE: No executable code has been changed—only comments were added.
#
# Key ideas covered in these annotations:
# - What the file does in the overall MCP + Microsoft Agent Framework (MAF) architecture.
# - How STDIO client/server works for MCP (JSON-RPC over stdin/stdout).
# - Where authentication, environment variables, and model settings are used.
# - How tools and agents are composed and exposed to clients like VS Code Copilot Agents.
##########################################################################################

# agent_as_mcp_azure.py
# Azure OpenAI–backed MCP stdio server (Microsoft Agent Framework) — featureful demo
# Adds: health_check, list_menu, dietary filter, multi-currency pricing, happy-hour specials.

import os, sys, signal, logging, json, math, datetime as dt
from typing import Annotated, Optional, Callable, Literal

import anyio
# MCP SERVER: stdio_server provides async stdin/stdout streams for JSON-RPC requests/responses.
from mcp.server.stdio import stdio_server

# Agent Framework (Azure)
# MAF AZURE RESPONSES CLIENT: Bridges to Azure OpenAI 'Responses' API to build an agent.
from agent_framework.azure import AzureOpenAIResponsesClient

# Azure identity
# Azure Identity: DefaultAzureCredential (env/MSI/VSCode/etc.) or AzureCliCredential for token acquisition.
from azure.identity import DefaultAzureCredential, AzureCliCredential

# Azure identity + .env
# Azure Identity: DefaultAzureCredential (env/MSI/VSCode/etc.) or AzureCliCredential for token acquisition.
from azure.identity import DefaultAzureCredential, AzureCliCredential
from dotenv import load_dotenv

# ---- Load .env (optional) ----
load_dotenv(override=False)


# ----------------- Logging -----------------
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
log = logging.getLogger("mcp_server")

# ----------------- Demo data -----------------
# A tiny in-memory "menu" with tags & allergens so we can do interesting queries.
MENU = [
    # name,          price_USD, category,            tags,                           allergens
    ("Clam Chowder", 7.99,      "soup",              ["seafood"],                    ["shellfish", "dairy", "gluten"]),
    ("Cobb Salad",   9.99,      "salad",             ["gluten-free"],                ["egg", "dairy"]),
    ("Chai Tea",     3.50,      "drink",             ["vegetarian"],                 ["dairy"]),
    ("Falafel Wrap", 8.75,      "mains",             ["vegan"],                      ["gluten", "sesame"]),
    ("Grilled Tofu", 11.50,     "mains",             ["vegan", "gluten-free"],       []),
    ("Cheesecake",   6.25,      "dessert",           ["vegetarian"],                 ["dairy", "gluten"]),
]

FX = {  # fun, fixed sample conversion (not live FX)
    "USD": 1.00,
    "GBP": 0.78,
    "EUR": 0.92,
    "INR": 83.00
}

# Function definition below:
def _money(amount_usd: float, currency: str) -> str:
    rate = FX.get(currency.upper(), 1.0)
    value = amount_usd * rate
    # simple formatting per currency
    symbol = {"USD": "$", "GBP": "£", "EUR": "€", "INR": "₹"}.get(currency.upper(), "$")
    return f"{symbol}{value:0.2f} {currency.upper()}"

# Function definition below:
def _json(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)

# ----------------- Tools -----------------
# Function definition below:
def health_check() -> Annotated[str, "Returns server and model configuration status in JSON."]:
    """Quick MCP health check so clients can validate connectivity & config."""
    status = {
        "status": "ok",
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
        "deployment": os.getenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"),
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION") or "preview",
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
        "auth_mode": ("api_key" if os.getenv("AZURE_OPENAI_API_KEY")
                      else ("azure_cli" if os.getenv("AZURE_USE_CLI") == "1" else "default_credential"))
    }
    return _json(status)

# Function definition below:
def list_menu(
    category: Annotated[Optional[str], "Optional category filter e.g. soup|mains|drink|salad|dessert"] = None
) -> Annotated[str, "Returns the full menu (JSON) with name, USD price, category, tags, allergens."]:
    items = []
    for name, usd, cat, tags, allergens in MENU:
        if category and cat.lower() != category.lower():
            continue
        items.append({"name": name, "price_usd": usd, "category": cat, "tags": tags, "allergens": allergens})
    return _json({"items": items, "count": len(items)})

# Function definition below:
def get_item_price(
    menu_item: Annotated[str, "Menu item name"],
    currency: Annotated[Literal["USD","GBP","EUR","INR"], "Currency code (USD, GBP, EUR, INR)"] = "USD"
) -> Annotated[str, "Returns the item price in the requested currency (JSON)."]:
    for name, usd, *_ in MENU:
        if name.lower() == menu_item.lower():
            return _json({"item": name, "price": _money(usd, currency), "currency": currency.upper()})
    # fuzzy-ish suggestion
    suggestions = [n for n, *_ in MENU if menu_item.lower() in n.lower()]
    return _json({"error": f"Item '{menu_item}' not found.", "did_you_mean": suggestions})

# Function definition below:
def find_by_diet(
    diet: Annotated[Literal["vegan","vegetarian","gluten-free"], "Diet tag to include"]
) -> Annotated[str, "List items matching a dietary preference (JSON)."]:
    out = [dict(name=n, category=c, price_usd=p, tags=t, allergens=a)
           for n,p,c,t,a in MENU if diet in t]
    return _json({"diet": diet, "items": out, "count": len(out)})

# Function definition below:
def happy_hour_specials(
    now_iso: Annotated[Optional[str], "Optional ISO datetime; default = current local time"] = None
) -> Annotated[str, "Returns time-aware specials with discount applied (JSON)."]:
    # 15% off drinks 16:00–18:59 local
    now = dt.datetime.fromisoformat(now_iso) if now_iso else dt.datetime.now()
    in_happy = 16 <= now.hour <= 18
    specials = []
    for name, usd, cat, tags, allergens in MENU:
        if cat == "drink":
            price = usd * (0.85 if in_happy else 1.0)
            specials.append({"name": name, "category": cat, "price_usd": round(price, 2),
                             "happy_hour": in_happy})
    return _json({"window": "16:00–18:59", "local_time": now.isoformat(timespec="seconds"),
                  "specials": specials})

# ----------------- Auth helpers -----------------
# Azure Cognitive Services scope used when acquiring AAD tokens for Azure OpenAI.
COGNITIVE_SCOPES = ("https://cognitiveservices.azure.com/.default",)

# Function definition below:
def build_ad_token_provider() -> Optional[Callable[[], str]]:
    """Return a callable that yields an AAD bearer token for Azure OpenAI, if no API key is set."""
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
    if os.getenv("AZURE_OPENAI_API_KEY"):
        return None
    if os.getenv("AZURE_USE_CLI") == "1":
# Azure Identity: DefaultAzureCredential (env/MSI/VSCode/etc.) or AzureCliCredential for token acquisition.
        cli_cred = AzureCliCredential()
        log.info("Auth: Azure CLI via ad_token_provider")
# Azure Cognitive Services scope used when acquiring AAD tokens for Azure OpenAI.
        return lambda: cli_cred.get_token(*COGNITIVE_SCOPES).token
# Azure Identity: DefaultAzureCredential (env/MSI/VSCode/etc.) or AzureCliCredential for token acquisition.
    dac = DefaultAzureCredential(exclude_interactive_browser_credential=True)
# Azure Identity: DefaultAzureCredential (env/MSI/VSCode/etc.) or AzureCliCredential for token acquisition.
    log.info("Auth: DefaultAzureCredential via ad_token_provider")
# Azure Cognitive Services scope used when acquiring AAD tokens for Azure OpenAI.
    return lambda: dac.get_token(*COGNITIVE_SCOPES).token

# ----------------- Build Agent -----------------
# build_agent(): Constructs the Agent Framework agent and registers python functions as tools.
def build_agent():
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
    endpoint   = os.getenv("AZURE_OPENAI_ENDPOINT")
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
    deployment = os.getenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME")
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
    api_version = os.getenv("AZURE_OPENAI_API_VERSION") or "preview"

# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
    missing = [n for n,v in [("AZURE_OPENAI_ENDPOINT",endpoint),
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
                             ("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME",deployment)] if not v]
    if missing:
        log.error("Missing env: %s", ", ".join(missing)); sys.exit(1)

# MAF AZURE RESPONSES CLIENT: Bridges to Azure OpenAI 'Responses' API to build an agent.
    client = AzureOpenAIResponsesClient(
        endpoint=endpoint,
        deployment_name=deployment,
        api_version=api_version,
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        ad_token_provider=build_ad_token_provider(),
    )

    # NOTE: This *exposes the agent as the single MCP tool*. The functions above are INTERNAL tools the agent can call.
    agent = client.create_agent(
        name="RestaurantAgent",
        description="Menu assistant with health check, dietary filters, FX pricing, and happy-hour logic.",
        tools=[health_check, list_menu, get_item_price, find_by_diet, happy_hour_specials],
        instructions=(
            "You are a precise and concise restaurant assistant.\n"
            "- Prefer returning short answers for natural questions.\n"
            "- When users ask for JSON, call the underlying tools and return their JSON as-is.\n"
            "- If users ask prices in currencies, use get_item_price with the 'currency' arg.\n"
            "- If users ask about vegan/vegetarian/gluten-free items, use find_by_diet.\n"
            "- For quick diagnostics, call health_check."
        ),
    )
    return agent

# ----------------- MCP stdio server -----------------
# run_server(): Starts the MCP stdio server and hands the server the read/write streams.
async def run_server():
    agent = build_agent()
    server = agent.as_mcp_server()
    log.info("Starting MCP stdio server (Ctrl+C to stop)")
# stdio_server(): Pairs the server with stdin/stdout to receive JSON-RPC requests and send responses.
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())

# ----------------- Supervisor -----------------
# supervisor(): Coordinates the server task and handles graceful shutdown on SIGINT/SIGTERM.
async def supervisor():
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
    log.info(f"Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
    log.info(f"Deployment: {os.getenv('AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME')}")
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
    log.info(f"API version: {os.getenv('AZURE_OPENAI_API_VERSION') or 'preview'}")
# ENV VAR: Azure OpenAI configuration (endpoint, deployment, api version, key).
    auth_mode = "api_key" if os.getenv("AZURE_OPENAI_API_KEY") else ("azure_cli" if os.getenv("AZURE_USE_CLI") == "1" else "default_credential")
    log.info("Auth mode: %s", auth_mode)

    async with anyio.create_task_group() as tg:
        tg.start_soon(run_server)
        try:
            with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
                async for _ in signals:
                    log.info("Shutdown signal received; stopping MCP server...")
                    tg.cancel_scope.cancel()
                    break
        except Exception:
            # limited signal support environments
            await anyio.Event().wait()

# main(): Entry point that runs the async supervisor with AnyIO.
def main():
    anyio.run(supervisor)

if __name__ == "__main__":
    main()
