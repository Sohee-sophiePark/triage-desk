"""LLM boundary: one request/response shape, three clients (live, cassette, scripted), PII redaction on every call."""
import hashlib
import json
import re
from pathlib import Path
from typing import Callable, Literal, Protocol

import litellm
from pydantic import BaseModel

from app.agents.config import agent_settings
from app.agents.pii_hooks import sanitize_llm_output

litellm.drop_params = True

_CANARY_LINE = re.compile(r"\n\nCANARY: .*", re.DOTALL)


class LLMRequest(BaseModel):
    purpose: str
    system: str
    user: str


class LLMResponse(BaseModel):
    data: dict
    source: Literal["live", "cassette", "scripted"]
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0


class LLMClient(Protocol):
    async def generate(self, req: LLMRequest) -> LLMResponse: ...


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].removeprefix("json")
    return json.loads(raw)


# Errors that mean "this model cannot serve right now"; anything else (bad request, auth) stops the chain.
FALLBACK_ERRORS = (litellm.RateLimitError, litellm.ServiceUnavailableError, litellm.NotFoundError,
                   litellm.PermissionDeniedError, litellm.BadRequestError, litellm.InternalServerError, litellm.Timeout,
                   litellm.APIConnectionError)


class LiveClient:
    """Real model call through LiteLLM (async, so parallel specialists overlap), falling back down MODELS."""

    def __init__(self, models: list[str] | None = None):
        self.models = models or agent_settings.MODELS

    async def generate(self, req: LLMRequest) -> LLMResponse:
        for i, model in enumerate(self.models):
            try:
                r = await litellm.acompletion(
                    model=model,
                    messages=[{"role": "system", "content": req.system}, {"role": "user", "content": req.user}],
                    temperature=agent_settings.TEMPERATURE,
                    max_tokens=agent_settings.MAX_TOKENS,
                    response_format={"type": "json_object"},
                    api_key=agent_settings.GEMINI_API_KEY,
                )
                break
            except FALLBACK_ERRORS:
                if i == len(self.models) - 1:
                    raise
        usage = getattr(r, "usage", None)
        return LLMResponse(
            data=_parse_json(r.choices[0].message.content),
            source="live",
            model=model,
            tokens_in=getattr(usage, "prompt_tokens", 0) or 0,
            tokens_out=getattr(usage, "completion_tokens", 0) or 0,
        )


class CassetteMiss(KeyError):
    pass


def request_key(req: LLMRequest) -> str:
    """Stable hash of a request; the per-run canary line is excluded so replays match."""
    payload = {"purpose": req.purpose, "system": _CANARY_LINE.sub("", req.system), "user": req.user}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class CassetteClient:
    """`record` calls `inner` and appends to a JSONL file; `replay` serves recorded responses only."""

    def __init__(self, path: Path, mode: Literal["record", "replay"], inner: LLMClient | None = None):
        self.path, self.mode, self.inner = path, mode, inner
        self.entries: dict[str, dict] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                entry = json.loads(line)
                self.entries[entry["key"]] = entry["response"]

    async def generate(self, req: LLMRequest) -> LLMResponse:
        key = request_key(req)
        if self.mode == "replay":
            if key not in self.entries:
                raise CassetteMiss(f"no cassette entry for {req.purpose} ({key[:12]})")
            return LLMResponse.model_validate(self.entries[key]).model_copy(update={"source": "cassette"})
        resp = await self.inner.generate(req)
        self.entries[key] = resp.model_dump()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "purpose": req.purpose, "response": resp.model_dump()}) + "\n")
        return resp


Responder = Callable[[LLMRequest], dict] | list


class ScriptedClient:
    """Serves canned responses per purpose: a list (popped in order; Exceptions are raised) or a callable."""

    def __init__(self, responders: dict[str, Responder]):
        self.responders = responders
        self.calls: list[LLMRequest] = []

    async def generate(self, req: LLMRequest) -> LLMResponse:
        self.calls.append(req)
        r = self.responders[req.purpose]
        item = r.pop(0) if isinstance(r, list) else r(req)
        if isinstance(item, Exception):
            raise item
        return LLMResponse(data=item, source="scripted")


def get_client() -> LLMClient:
    path = Path(agent_settings.CASSETTE_PATH)
    if agent_settings.LLM_MODE == "replay":
        return CassetteClient(path, "replay")
    if agent_settings.LLM_MODE == "record":
        return CassetteClient(path, "record", LiveClient())
    return LiveClient()


async def ask(client: LLMClient, purpose: str, system: str, payload: dict, schema: type[BaseModel]):
    """Redact PII from the payload, call the model, validate the JSON against `schema`."""
    user = sanitize_llm_output(json.dumps(payload, sort_keys=True, default=str))
    resp = await client.generate(LLMRequest(purpose=purpose, system=system, user=user))
    return schema.model_validate(resp.data), resp
