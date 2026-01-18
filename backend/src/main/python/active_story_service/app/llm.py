import os, httpx

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

async def anthropic_messages(system, messages, max_tokens=600):
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        return "".join(b.get("text","") for b in data.get("content", []) if b.get("type")=="text")
