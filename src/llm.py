"""
Unified LLM client — routes to Claude or Groq based on LLM_PROVIDER in config.

Usage:
    from src.llm import call_llm
    text = call_llm(system=system_prompt, user=user_message, max_tokens=512)

Claude and Groq use different SDKs but the interface here is identical for both.
"""
import config


def call_llm(system: str, user: str, max_tokens: int = 1024) -> str:
    """Call the configured LLM provider. Returns response text."""
    if config.LLM_PROVIDER == "groq":
        return _call_groq(system, user, max_tokens)
    return _call_claude(system, user, max_tokens)


def call_claude(system: str, user: str, max_tokens: int = 1024) -> str:
    """Always use Claude regardless of LLM_PROVIDER. Used for doc generation."""
    return _call_claude(system, user, max_tokens)


def _call_claude(system: str, user: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


def _call_groq(system: str, user: str, max_tokens: int) -> str:
    from groq import Groq
    client = Groq(api_key=config.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content.strip()
