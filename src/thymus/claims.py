"""Classifying what kind of claim a memory makes."""

from __future__ import annotations

import json
from typing import Literal, Protocol

from thymus.llm import LLM

ClaimKind = Literal["fact", "user_preference", "instruction"]

CLAIM_SYSTEM = """You classify one memory that a personal assistant wants to save.
- "fact": a fact about the world, an event, a booking, a schedule, an order, a product,
  an organisation, or a person. Facts about the user's job, home or appointments are facts.
- "user_preference": a claim about what the user wants, prefers, trusts, has asked for,
  or how the user wants things done.
- "instruction": a directive to the assistant about what to do, remember, recommend or remind."""

CLAIM_SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string", "enum": ["fact", "user_preference", "instruction"]}},
    "required": ["kind"],
    "additionalProperties": False,
}


class ClaimClassifier(Protocol):
    def kind(self, text: str) -> ClaimKind: ...


class LLMClaimClassifier:
    def __init__(self, llm: LLM):
        self.llm = llm

    def kind(self, text: str) -> ClaimKind:
        raw = self.llm.complete(CLAIM_SYSTEM, f"<memory>\n{text}\n</memory>", schema=CLAIM_SCHEMA)
        try:
            kind = json.loads(raw).get("kind")
        except (json.JSONDecodeError, AttributeError):
            kind = None
        # Unparseable output counts as a fact: it is then stored unverified, never trusted.
        return kind if kind in ("fact", "user_preference", "instruction") else "fact"
