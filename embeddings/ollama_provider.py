"""Ollama embedding backend — zero Python ML deps.

Talks to a local Ollama server over HTTP (http://localhost:11434/api/embeddings).
Default model: nomic-embed-text (768 dims). No sentence-transformers / torch required.

Env-var precedence (highest first):
  - CKG_OLLAMA_URL / CKG_OLLAMA_HOST (CKG-specific override)
  - OLLAMA_HOST (ollama's own var)
  - default http://localhost:11434
Similarly for model:
  - CKG_OLLAMA_MODEL
  - OLLAMA_MODEL
  - default nomic-embed-text
Timeout: CKG_OLLAMA_TIMEOUT (seconds), default 60s.

Previous CKG fastembed bug #67 (cache in /tmp cleared on reboot) does not
apply here — Ollama stores models outside Python's temp dir — but we keep
the same env-var layering reasoning so users can isolate CKG's Ollama
endpoint from other tools sharing Ollama.
"""
import os

import numpy as np

from embeddings.provider import EmbeddingProvider

_DEFAULT_OLLAMA_URL = "http://localhost:11434"
_DEFAULT_OLLAMA_MODEL = "nomic-embed-text"
_DEFAULT_TIMEOUT = 60.0
_MAX_EMBED_CHARS = 3000


def _resolve_ollama_url(explicit: str | None = None) -> str:
    if explicit:
        return explicit.rstrip("/")
    for var in ("CKG_OLLAMA_URL", "CKG_OLLAMA_HOST", "OLLAMA_HOST"):
        val = os.environ.get(var, "").strip()
        if val:
            # OLLAMA_HOST may be like "http://localhost:11434" or "localhost:11434"
            if not val.startswith("http"):
                val = f"http://{val}"
            return val.rstrip("/")
    return _DEFAULT_OLLAMA_URL


def _resolve_ollama_model(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    for var in ("CKG_OLLAMA_MODEL", "OLLAMA_MODEL"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    return _DEFAULT_OLLAMA_MODEL


def _resolve_timeout(explicit: float | None = None) -> float:
    if explicit is not None:
        return explicit
    raw = os.environ.get("CKG_OLLAMA_TIMEOUT", "").strip()
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return _DEFAULT_TIMEOUT


def ollama_available(base_url: str | None = None) -> bool:
    """Cheap reachability probe — does Ollama answer on /api/tags?"""
    url = _resolve_ollama_url(base_url)
    try:
        # Use httpx if present (via mcp), else urllib
        try:
            import httpx

            resp = httpx.get(f"{url}/api/tags", timeout=1.5)
            return resp.status_code == 200
        except ImportError:
            import urllib.request

            req = urllib.request.Request(f"{url}/api/tags")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
    except Exception:  # noqa: BLE001 -- probe must return False on any network/client error
        return False


class OllamaEmbeddingProvider(EmbeddingProvider):
    name = "ollama"

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._model_name = _resolve_ollama_model(model_name)
        self._base_url = _resolve_ollama_url(base_url)
        self._timeout = _resolve_timeout(timeout)
        # Probe dimension
        probe = self._embed_batch(["_"])
        if not probe or not probe[0]:
            raise RuntimeError(
                f"Ollama at {self._base_url} returned no embedding for model '{self._model_name}'. "
                f"Verify with `ollama pull {self._model_name}` and that the server is running."
            )
        self._dimension = len(probe[0])

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_id(self) -> str:
        return f"ollama:{self._model_name}:{self._dimension}"

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed(self, text: str) -> np.ndarray:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)
        vectors = self._embed_batch(texts)
        # Filter empty vectors for empty inputs (already handled) - ensure shape
        arr = np.array(vectors, dtype=np.float32)
        if arr.shape[0] != len(texts):
            # Handle skipped empties: _embed_batch returns list aligned to input
            arr = np.stack([np.zeros(self._dimension, dtype=np.float32) if not v else np.array(v, dtype=np.float32) for v in vectors])
        # Normalize like local provider
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        return arr / norms

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed(query)

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Truncate and skip empties
        safe_texts: list[str] = []
        orig_indices: list[int] = []
        for i, t in enumerate(texts):
            if not t or not t.strip():
                continue
            safe_texts.append(t[:_MAX_EMBED_CHARS])
            orig_indices.append(i)

        if not safe_texts:
            return [[] for _ in texts]

        # Try httpx first
        try:
            import httpx

            resp = httpx.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model_name, "input": safe_texts},
                timeout=self._timeout,
            )
            # Fallback to /api/embeddings if /api/embed not found (older Ollama)
            if resp.status_code == 404:
                resp = httpx.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model_name, "prompt": safe_texts[0] if len(safe_texts) == 1 else safe_texts},
                    timeout=self._timeout,
                )
                # Ollama /api/embeddings expects single prompt, not batch - handle single
                if len(safe_texts) > 1:
                    # Fall back to one-at-a-time
                    return self._embed_batch_one_by_one(safe_texts, orig_indices, len(texts))
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings", [])
            # Some Ollama versions return {"embedding": [...]} for single
            if not embeddings and "embedding" in data:
                embeddings = [data["embedding"]]
        except ImportError:
            embeddings = self._embed_via_urllib(safe_texts)
        except Exception as exc:
            # Batch failed, retry one-at-a-time
            if "400" in str(exc) or "context length" in str(exc).lower():
                return self._embed_batch_one_by_one(safe_texts, orig_indices, len(texts))
            raise

        # Map back to original positions
        result: list[list[float]] = [[] for _ in texts]
        for idx, emb in zip(orig_indices, embeddings):
            result[idx] = emb
        return result

    def _embed_batch_one_by_one(self, safe_texts, orig_indices, orig_len) -> list[list[float]]:
        result: list[list[float]] = [[] for _ in range(orig_len)]
        for orig_idx, text in zip(orig_indices, safe_texts):
            vec = self._embed_single(text)
            result[orig_idx] = vec
        return result

    def _embed_single(self, text: str) -> list[float]:
        # Halve on context length error
        while text:
            try:
                import httpx

                resp = httpx.post(
                    f"{self._base_url}/api/embed",
                    json={"model": self._model_name, "input": [text]},
                    timeout=self._timeout,
                )
                if resp.status_code == 400 and "context length" in resp.text:
                    text = text[: len(text) // 2]
                    continue
                resp.raise_for_status()
                data = resp.json()
                embs = data.get("embeddings", [])
                if embs:
                    return embs[0]
                if "embedding" in data:
                    return data["embedding"]
                return []
            except ImportError:
                return self._embed_via_urllib([text])[0] if text else []
        return []

    def _embed_via_urllib(self, texts: list[str]) -> list[list[float]]:
        import json
        import urllib.error
        import urllib.request

        payload = json.dumps({"model": self._model_name, "input": texts}).encode()
        req = urllib.request.Request(
            f"{self._base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode())
                return data.get("embeddings", [])
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Try legacy /api/embeddings with single prompt
                if len(texts) == 1:
                    payload2 = json.dumps({"model": self._model_name, "prompt": texts[0]}).encode()
                    req2 = urllib.request.Request(
                        f"{self._base_url}/api/embeddings",
                        data=payload2,
                        headers={"Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(req2, timeout=self._timeout) as resp2:
                        data2 = json.loads(resp2.read().decode())
                        if "embedding" in data2:
                            return [data2["embedding"]]
                raise RuntimeError(f"Ollama model {self._model_name} not found at {self._base_url}") from e
            raise
