"""Provider streaming functions: raw httpx SSE.

Each function takes a ChatCompletionForm + url + key.
All yield normalized events: text_delta, tool_call, usage, done.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Dict, List

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ChatCompletionForm(BaseModel):
    """Mirrors OpenAI Responses API request shape."""
    model: str
    messages: List[Dict]
    instructions: str = ""
    tools: List[Dict] = []


# ── Anthropic ────────────────────────────────────────────────


def _to_anthropic_messages(messages: list[dict]) -> list[dict]:
    """Canonical messages → Anthropic format."""
    result = []
    for m in messages:
        role = m["role"]
        if role == "system":
            continue  # system goes in body.system
        content = m.get("content", "")
        if role == "tool":
            # tool result → Anthropic tool_result block
            result.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": m.get("tool_call_id", ""),
                    "content": content,
                }],
            })
        elif role == "assistant" and m.get("tool_calls"):
            # assistant with tool calls → Anthropic tool_use blocks
            blocks: list[dict] = []
            if content:
                blocks.append({"type": "text", "text": content})
            for tc in m["tool_calls"]:
                blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id", ""),
                    "name": tc["function"]["name"],
                    "input": json.loads(tc["function"].get("arguments", "{}")),
                })
            result.append({"role": "assistant", "content": blocks})
        else:
            result.append({"role": role, "content": content})
    return result


async def stream_anthropic(
    form_data: ChatCompletionForm, url: str, key: str
) -> AsyncIterator[dict]:
    tools = [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["parameters"],
        }
        for t in form_data.tools
    ]

    body = {
        "model": form_data.model,
        "system": form_data.instructions,
        "messages": _to_anthropic_messages(form_data.messages),
        "tools": tools if tools else None,
        "stream": True,
        "max_tokens": 4096,
    }
    # Remove None values
    body = {k: v for k, v in body.items() if v is not None}
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}

    async with httpx.AsyncClient(timeout=httpx.Timeout(30, read=300)) as client:
        logger.info("[stream] anthropic POST %s/messages model=%s", url, form_data.model)
        async with client.stream(
            "POST", f"{url}/messages", json=body, headers=headers
        ) as resp:
            logger.info("[stream] anthropic status=%s", resp.status_code)
            resp.raise_for_status()
            current_block: dict = {}
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                etype = event.get("type")

                if etype == "content_block_start":
                    block = event["content_block"]
                    current_block = {"type": block["type"], "index": event["index"]}
                    if block["type"] == "tool_use":
                        current_block["id"] = block["id"]
                        current_block["name"] = block["name"]
                        current_block["input_json"] = ""

                elif etype == "content_block_delta":
                    delta = event["delta"]
                    if delta["type"] == "text_delta":
                        yield {"type": "text_delta", "content": delta["text"]}
                    elif delta["type"] == "input_json_delta":
                        current_block["input_json"] += delta["partial_json"]

                elif etype == "content_block_stop":
                    if current_block.get("type") == "tool_use":
                        yield {
                            "type": "tool_call",
                            "call_id": current_block["id"],
                            "name": current_block["name"],
                            "arguments": json.loads(current_block["input_json"]),
                        }

                elif etype == "message_delta":
                    usage = event.get("usage", {})
                    if usage:
                        yield {"type": "usage", **usage}

                elif etype == "message_stop":
                    yield {"type": "done"}


# ── OpenAI Chat Completions ──────────────────────────────────


def _to_openai_messages(messages: list[dict], instructions: str) -> list[dict]:
    """Canonical messages → OpenAI Chat Completions format."""
    result = []
    if instructions:
        result.append({"role": "system", "content": instructions})
    for m in messages:
        if m["role"] == "system":
            continue
        result.append(m)
    return result


async def stream_openai_completions(
    form_data: ChatCompletionForm, url: str, key: str
) -> AsyncIterator[dict]:
    tools = [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in form_data.tools
    ]

    body: dict = {
        "model": form_data.model,
        "messages": _to_openai_messages(form_data.messages, form_data.instructions),
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if tools:
        body["tools"] = tools
    headers = {"Authorization": f"Bearer {key}"}

    async with httpx.AsyncClient(timeout=httpx.Timeout(30, read=300)) as client:
        logger.info("[stream] openai completions POST %s/chat/completions model=%s", url, form_data.model)
        async with client.stream(
            "POST", f"{url}/chat/completions", json=body, headers=headers
        ) as resp:
            logger.info("[stream] openai completions status=%s", resp.status_code)
            resp.raise_for_status()
            tool_calls: dict[int, dict] = {}
            async for line in resp.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                chunk = json.loads(line[6:])
                choices = chunk.get("choices", [])
                delta = choices[0].get("delta", {}) if choices else {}

                if delta.get("content"):
                    yield {"type": "text_delta", "content": delta["content"]}

                for tc in delta.get("tool_calls", []):
                    idx = tc["index"]
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "arguments_json": "",
                        }
                    tool_calls[idx]["arguments_json"] += tc["function"].get(
                        "arguments", ""
                    )

                if choices and choices[0].get("finish_reason") == "tool_calls":
                    for tc in tool_calls.values():
                        yield {
                            "type": "tool_call",
                            "call_id": tc["id"],
                            "name": tc["name"],
                            "arguments": json.loads(tc["arguments_json"]),
                        }

                if chunk.get("usage"):
                    yield {"type": "usage", **chunk["usage"]}

            yield {"type": "done"}


# ── OpenAI Responses API ─────────────────────────────────────


def _to_responses_input(messages: list[dict], instructions: str) -> list[dict]:
    """Canonical messages → Responses API input items."""
    items = []
    for m in messages:
        role = m["role"]
        if role == "system":
            continue
        if role == "tool":
            items.append({
                "type": "function_call_output",
                "call_id": m.get("tool_call_id", ""),
                "output": m.get("content", ""),
            })
        elif role == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                items.append({
                    "type": "function_call",
                    "id": tc.get("id", ""),
                    "call_id": tc.get("id", ""),
                    "name": tc["function"]["name"],
                    "arguments": tc["function"].get("arguments", "{}"),
                })
        else:
            items.append({"role": role, "content": m.get("content", "")})
    return items


async def stream_openai_responses(
    form_data: ChatCompletionForm, url: str, key: str
) -> AsyncIterator[dict]:
    tools = [
        {
            "type": "function",
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"],
        }
        for t in form_data.tools
    ]

    body: dict = {
        "model": form_data.model,
        "input": _to_responses_input(form_data.messages, form_data.instructions),
        "stream": True,
    }
    if form_data.instructions:
        body["instructions"] = form_data.instructions
    if tools:
        body["tools"] = tools
    headers = {"Authorization": f"Bearer {key}"}

    async with httpx.AsyncClient(timeout=httpx.Timeout(30, read=300)) as client:
        logger.info("[stream] openai responses POST %s/responses model=%s", url, form_data.model)
        async with client.stream(
            "POST", f"{url}/responses", json=body, headers=headers
        ) as resp:
            logger.info("[stream] openai responses status=%s", resp.status_code)
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                etype = event.get("type")

                if etype == "response.output_text.delta":
                    yield {"type": "text_delta", "content": event["delta"]}

                elif etype == "response.output_item.done":
                    item = event["item"]
                    if item["type"] == "function_call":
                        yield {
                            "type": "tool_call",
                            "call_id": item["call_id"],
                            "name": item["name"],
                            "arguments": json.loads(item["arguments"]),
                        }

                elif etype == "response.completed":
                    usage = event.get("response", {}).get("usage", {})
                    if usage:
                        yield {"type": "usage", **usage}
                    yield {"type": "done"}
