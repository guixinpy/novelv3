from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Protocol

import httpx


DEFAULT_LOCAL_DIMENSIONS = 96


class EmbeddingProvider(Protocol):
    provider_name: str
    model_name: str
    dimensions: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


class LocalHashEmbeddingProvider:
    provider_name = "local"
    model_name = "hash-bigram-v1"

    def __init__(self, dimensions: int = DEFAULT_LOCAL_DIMENSIONS):
        self.dimensions = dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in tokenize_for_retrieval(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 else -1.0
            vector[index] += sign * (1.0 + min(len(token), 6) * 0.08)
        return normalize_vector(vector)


class OpenAICompatibleEmbeddingProvider:
    provider_name = "remote"

    def __init__(self, *, api_key: str, base_url: str, model_name: str, dimensions: int):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.dimensions = dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            f"{self.base_url}/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model_name, "input": texts},
            timeout=60.0,
        )
        response.raise_for_status()
        payload = response.json()
        vectors = [item["embedding"] for item in sorted(payload["data"], key=lambda item: item["index"])]
        return [normalize_vector([float(value) for value in vector]) for vector in vectors]


def get_embedding_provider() -> EmbeddingProvider:
    provider_mode = os.getenv("EMBEDDING_PROVIDER", "local").strip().lower()
    api_key = os.getenv("EMBEDDING_API_KEY", "").strip()
    model = os.getenv("EMBEDDING_MODEL", "").strip()
    if provider_mode == "remote" and api_key and model:
        base_url = os.getenv("EMBEDDING_API_BASE", "https://api.openai.com").strip()
        dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", str(DEFAULT_LOCAL_DIMENSIONS)))
        return OpenAICompatibleEmbeddingProvider(
            api_key=api_key,
            base_url=base_url,
            model_name=model,
            dimensions=dimensions,
        )
    return LocalHashEmbeddingProvider()


def tokenize_for_retrieval(text: str) -> list[str]:
    normalized = normalize_text(text)
    latin_tokens = re.findall(r"[a-z0-9_]+", normalized)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", normalized)
    cjk_bigrams = ["".join(cjk_chars[index : index + 2]) for index in range(max(len(cjk_chars) - 1, 0))]
    cjk_trigrams = ["".join(cjk_chars[index : index + 3]) for index in range(max(len(cjk_chars) - 2, 0))]
    return [token for token in [*latin_tokens, *cjk_bigrams, *cjk_trigrams] if token]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def normalize_vector(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude <= 0:
        return vector
    return [value / magnitude for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))


def vector_hash(vector: list[float]) -> str:
    rounded = ",".join(f"{value:.6f}" for value in vector)
    return hashlib.sha256(rounded.encode("utf-8")).hexdigest()
