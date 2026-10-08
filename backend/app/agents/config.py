from typing import Literal, Optional

from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    # Free-tier stable text models only, newest first; the live client falls back down the list on
    # quota/availability errors. Override with MODELS='["gemini/...", ...]' in .env (free tier only).
    MODELS: list[str] = [
        "gemini/gemini-3.8-flash",
        "gemini/gemini-3.7-flash",
        "gemini/gemini-3.6-flash",
        "gemini/gemini-3.5-flash",
        "gemini/gemini-3.5-flash-lite",
        "gemini/gemini-3.1-flash-lite",
        "gemini/gemini-2.5-flash",       # 2.5: Google limits access to projects that used it before
        "gemini/gemini-2.5-flash-lite",
    ]
    TEMPERATURE: float = 0.1
    MAX_TOKENS: int = 2048

    # live = real model · record = live + append to cassette · replay = cassette only, no key needed
    LLM_MODE: Literal["live", "record", "replay"] = "live"
    CASSETTE_PATH: str = "cassettes/cases.jsonl"

    MAX_REVISIONS: int = 2      # writer re-drafts after a gate or evaluator failure
    EVAL_PASS_SCORE: int = 4    # every rubric score (1-5) must reach this

    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"


agent_settings = AgentSettings()
