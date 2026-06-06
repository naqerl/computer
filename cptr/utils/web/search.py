"""Search dispatcher: picks provider based on config.

Priority in auto mode:
1. Exa      (EXA_API_KEY or web.exa_api_key)
2. Tavily   (TAVILY_API_KEY or web.tavily_api_key)
3. Brave    (BRAVE_API_KEY or web.brave_api_key)
4. DuckDuckGo (zero-config fallback)
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


async def _get_key(env_var: str, config_key: str) -> str:
    """Check env var first, then DB config."""
    val = os.environ.get(env_var, "")
    if val:
        return val
    try:
        from cptr.models import Config
        return (await Config.get(config_key)) or ""
    except Exception:
        return ""


async def _get_config(key: str) -> str:
    """Read a single config value from DB."""
    try:
        from cptr.models import Config
        return (await Config.get(key)) or ""
    except Exception:
        return ""


async def web_search_handler(query: str) -> str:
    """Search the web using the configured or best available provider."""
    from cptr.utils.web import exa, tavily, brave, duckduckgo

    # Check if web access is disabled by admin
    enabled = await _get_config("web.enabled")
    if enabled == "false" or enabled is False:
        return "Error: web search is disabled by the administrator."

    provider = await _get_config("web.search_provider") or "auto"

    exa_key = await _get_key("EXA_API_KEY", "web.exa_api_key")
    tavily_key = await _get_key("TAVILY_API_KEY", "web.tavily_api_key")
    brave_key = await _get_key("BRAVE_API_KEY", "web.brave_api_key")

    # Explicit provider mode
    if provider != "auto":
        try:
            if provider == "exa":
                if not exa_key:
                    return "Error: Exa API key not configured."
                return await exa.search(query, exa_key)
            elif provider == "tavily":
                if not tavily_key:
                    return "Error: Tavily API key not configured."
                return await tavily.search(query, tavily_key)
            elif provider == "brave":
                if not brave_key:
                    return "Error: Brave API key not configured."
                return await brave.search(query, brave_key)
            elif provider == "duckduckgo":
                return await duckduckgo.search(query)
            else:
                return f"Error: unknown search provider '{provider}'."
        except Exception as e:
            logger.error("Search provider %s failed: %s", provider, e)
            return f"Error: {provider} search failed. {e}"

    # Auto mode: try each provider with a key, fall back to DuckDuckGo
    providers = []
    if exa_key:
        providers.append(("exa", lambda: exa.search(query, exa_key)))
    if tavily_key:
        providers.append(("tavily", lambda: tavily.search(query, tavily_key)))
    if brave_key:
        providers.append(("brave", lambda: brave.search(query, brave_key)))
    providers.append(("duckduckgo", lambda: duckduckgo.search(query)))

    for name, fn in providers:
        try:
            return await fn()
        except Exception as e:
            logger.warning("Search provider %s failed: %s", name, e)
            continue

    return "Error: all search providers failed."
