"""Text embedders used for memory recall."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

from thymus.llm import post_json

Vector = list[float]


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[Vector]: ...


def cosine(a: Vector, b: Vector) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class OllamaEmbedder:
    """Semantic embeddings from a local Ollama model such as nomic-embed-text."""

    def __init__(self, model: str = "nomic-embed-text", host: str = "http://localhost:11434", timeout: float = 120):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.name = f"ollama:{model}"

    def embed(self, texts: list[str]) -> list[Vector]:
        body = {"model": self.model, "input": texts}
        return post_json(f"{self.host}/api/embed", body, self.timeout)["embeddings"]


class MemoEmbedder:
    """Remembers vectors by text for the length of a run. Every gate re-embeds the same
    memories, and long-memory runs add the same background facts to every scenario."""

    def __init__(self, inner: Embedder):
        self.inner = inner
        self.name = inner.name
        self._vectors: dict[str, Vector] = {}

    def embed(self, texts: list[str]) -> list[Vector]:
        missing = [t for t in dict.fromkeys(texts) if t not in self._vectors]
        if missing:
            self._vectors.update(zip(missing, self.inner.embed(missing)))
        return [self._vectors[t] for t in texts]


_STOPWORDS = frozenset(
    "a an and are as at be by can could do does for from has have how i in is it its me my "
    "of on or our should so that the their them then there these they this to was we were "
    "what when where which who why will with you your".split()
)
_WORD = re.compile(r"[a-z0-9]+")


class HashEmbedder:
    """Offline bag-of-words embedder. Lexical only: good enough for tests and smoke
    runs, not for real experiments."""

    name = "hash"

    def __init__(self, dim: int = 512):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[Vector]:
        vectors = []
        for text in texts:
            vector = [0.0] * self.dim
            for word in _WORD.findall(text.lower()):
                if word in _STOPWORDS:
                    continue
                digest = hashlib.blake2b(word.encode(), digest_size=8).digest()
                vector[int.from_bytes(digest, "little") % self.dim] += 1.0
            vectors.append(vector)
        return vectors
