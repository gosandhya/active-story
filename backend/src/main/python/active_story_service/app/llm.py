import os, httpx
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent.parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Model options
HAIKU = "claude-3-haiku-20240307"
SONNET = "claude-3-haiku-20240307"  # Testing with Haiku first


async def anthropic_messages(system, messages, max_tokens=600, model=HAIKU):
    """
    Call Anthropic API with specified model.
    Default is Haiku for speed/cost. Use Sonnet for creative tasks.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    headers = {
        "x-api-key": api_key,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        return "".join(b.get("text","") for b in data.get("content", []) if b.get("type")=="text")
