"""Optional LLM narrative layer.

LLM is used ONLY for human-readable text (report explanation, chat replies).
All metrics and facts come from real ML code. Without LLM_API_KEY, or on any
error, deterministic template text is returned instead.
"""
import httpx

from ..config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def llm_available() -> bool:
    return bool(LLM_API_KEY)


def narrate(instruction: str, context: str, fallback: str) -> str:
    if not LLM_API_KEY:
        return fallback
    try:
        resp = httpx.post(
            f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are the Mlution ML agent. Reply in clear English, 2-4 sentences, "
                        "no invented numbers: use only facts from the provided context. Return plain text.",
                    },
                    {"role": "user", "content": f"{instruction}\n\nContext:\n{context}"},
                ],
                "max_tokens": 300,
                "temperature": 0.3,
            },
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            timeout=20.0,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return text or fallback
    except Exception:
        return fallback
