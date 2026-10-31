"""Bounded public WebRTC calls. No official-data, dossier or report tools."""
import asyncio
from dataclasses import dataclass

from .sessions import MissingSession
from .project_profile import project_instructions

CALL_SECONDS = 480
REPLY_TOKEN_BUDGET = 2048


def call_configuration(language, model):
    return {
        "type": "realtime", "model": model, "output_modalities": ["audio"],
        # Realtime's output budget includes audio; 250 can cut normal sentences.
        "max_output_tokens": REPLY_TOKEN_BUDGET, "tools": [], "tool_choice": "none",
        "audio": {"input": {"noise_reduction": {"type": "near_field"},
                            "turn_detection": {"type": "semantic_vad", "eagerness": "medium",
                                               "create_response": True, "interrupt_response": True}},
                  "output": {"voice": "marin"}},
        "instructions": project_instructions(language),
    }


class CallBusy(Exception):
    pass


@dataclass
class Call:
    provider_id: str
    timer: asyncio.Task


class RealtimeCalls:
    def __init__(self, provider, sessions, *, max_calls=4, duration=CALL_SECONDS):
        self.provider = provider
        self.sessions = sessions
        self.max_calls = max_calls
        self.duration = duration
        self.calls: dict[str, Call | None] = {}

    async def create(self, token, offer):
        if token in self.calls or len(self.calls) >= self.max_calls:
            raise CallBusy()
        language, _ = self.sessions.audio_begin(token)
        self.calls[token] = None  # Reserve before the first await.
        try:
            answer, provider_id = await self.provider.create_realtime(offer, language, token)
            if token not in self.calls:
                await self.provider.close_realtime(provider_id)
                raise MissingSession()
            try:
                seconds = min(self.duration, self.sessions.remaining(token))
            except MissingSession:
                await self.provider.close_realtime(provider_id)
                raise
            timer = asyncio.create_task(self._expire(token, seconds))
            self.calls[token] = Call(provider_id, timer)
            return answer, seconds
        except BaseException:
            await self.end(token)
            raise
        finally:
            try:
                self.sessions.audio_end(token)
            except MissingSession:
                await self.end(token)
                raise

    async def _expire(self, token, seconds):
        await asyncio.sleep(seconds)
        await self.end(token)

    async def end(self, token):
        call = self.calls.pop(token, None)
        if call:
            if call.timer is not asyncio.current_task():
                call.timer.cancel()
            await self.provider.close_realtime(call.provider_id)

    async def close(self):
        for token in list(self.calls):
            await self.end(token)
