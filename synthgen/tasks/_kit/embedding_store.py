"""Embedding-based task similarity gate using Google text-embedding-004 + LanceDB."""

from __future__ import annotations

import asyncio
from typing import Any

import lancedb
import numpy as np
import pyarrow as pa
from google import genai

from config import EMBEDDING_MODEL, GOOGLE_API_KEY, LANCEDB_PATH, SIMILARITY_THRESHOLD

EMBEDDING_DIM = 3072
BATCH_LIMIT = 100  # Google API max texts per request

TASK_FIELDS_FOR_EMBEDDING = [
    "task_title", "goal_summary", "realism_hooks",
    "multimodal_assets", "memory_file",
]


def _task_to_text(task: dict) -> str:
    """Concatenate narrative-unique fields into an embeddable string.

    Only fields that differentiate tasks are included — structural/boilerplate
    fields (privacy_scenario, tool_tiers, persona_voice, etc.) are excluded
    because they inflate similarity scores without reflecting real uniqueness.
    """
    parts: list[str] = []
    for field in TASK_FIELDS_FOR_EMBEDDING:
        val = task.get(field, "")
        if val is None:
            continue
        if isinstance(val, list):
            parts.append(" ".join(str(v) for v in val))
        elif isinstance(val, dict):
            parts.append(" ".join(f"{k}: {v}" for k, v in val.items()))
        else:
            parts.append(str(val))

    # Include milestone text from conversation_arc (most differentiating content)
    for step in task.get("conversation_arc", []):
        milestone = step.get("milestone", "")
        if milestone:
            parts.append(milestone)

    return " ".join(parts).strip()


NARRATIVE_FIELDS = ["task_title", "goal_summary", "realism_hooks"]


def _task_to_narrative_text(task: dict) -> str:
    """Narrative-only embedding for cross-batch novelty check.

    Uses only title, goal, realism hooks, and conversation arc user intents —
    excludes structural fields (PII labels, tool names, skill slugs) that inflate
    similarity scores between same-domain tasks.
    """
    parts: list[str] = []
    for field in NARRATIVE_FIELDS:
        val = task.get(field, "")
        if not val:
            continue
        if isinstance(val, list):
            parts.append(" ".join(str(v) for v in val))
        elif isinstance(val, dict):
            parts.append(" ".join(f"{k}: {v}" for k, v in val.items()))
        else:
            parts.append(str(val))
    for step in task.get("conversation_arc", []):
        intent = step.get("user_intent", "")
        if intent:
            parts.append(intent[:100])
    return " ".join(parts).strip()


class EmbeddingStore:
    """Manages task embeddings in LanceDB with Google text-embedding-004."""

    def __init__(
        self,
        db_path: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        threshold: float | None = None,
    ):
        self.db_path = str(db_path or LANCEDB_PATH)
        self.api_key = api_key or GOOGLE_API_KEY
        self.model = model or EMBEDDING_MODEL
        self.threshold = threshold if threshold is not None else SIMILARITY_THRESHOLD
        self.client = genai.Client(api_key=self.api_key)
        self.db = lancedb.connect(self.db_path)
        self.table = self._get_or_create_table()

    def _list_table_names(self) -> list[str]:
        """Get list of table names from LanceDB (handles API variations)."""
        result = self.db.list_tables()
        if hasattr(result, "tables"):
            return result.tables
        if isinstance(result, list):
            return result
        return list(result)

    def _get_or_create_table(self):
        """Get existing table or create a new one."""
        table_name = "task_embeddings"
        if table_name in self._list_table_names():
            return self.db.open_table(table_name)

        schema = pa.schema([
            pa.field("task_id", pa.string()),
            pa.field("persona_id", pa.string()),
            pa.field("text_fingerprint", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
        ])
        return self.db.create_table(table_name, schema=schema)

    def drop_table(self):
        """Drop the embeddings table and recreate it."""
        table_name = "task_embeddings"
        if table_name in self._list_table_names():
            self.db.drop_table(table_name)
        self.table = self._get_or_create_table()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Call Google text-embedding-004 to embed a list of texts."""
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), BATCH_LIMIT):
            batch = texts[i : i + BATCH_LIMIT]
            response = self.client.models.embed_content(
                model=self.model,
                contents=batch,
            )
            for embedding in response.embeddings:
                all_embeddings.append(embedding.values)

        return all_embeddings

    def check_batch(
        self, tasks: list[dict], threshold: float | None = None
    ) -> tuple[list[dict], list[dict]]:
        """Embed tasks and check similarity against the DB.

        Returns:
            (accepted, flagged) - accepted tasks pass novelty check,
            flagged tasks exceed similarity threshold.
        """
        if not tasks:
            return [], []

        thresh = threshold if threshold is not None else self.threshold
        texts = [_task_to_text(t) for t in tasks]
        embeddings = self.embed_texts(texts)

        accepted: list[dict] = []
        flagged: list[dict] = []

        table_count = self.table.count_rows()

        for i, (task, embedding) in enumerate(zip(tasks, embeddings)):
            is_similar = False

            # Check against existing DB entries (cross-persona / cross-batch novelty)
            if table_count > 0:
                results = (
                    self.table.search(embedding)
                    .metric("cosine")
                    .limit(5)
                    .to_pandas()
                )
                if not results.empty:
                    # LanceDB returns _distance (cosine distance), similarity = 1 - distance
                    max_similarity = 1.0 - results["_distance"].min()
                    if max_similarity >= thresh:
                        similar_id = results.iloc[results["_distance"].idxmin()]["task_id"]
                        task["_flagged_reason"] = (
                            f"similarity={max_similarity:.3f} with {similar_id}"
                        )
                        is_similar = True

            if is_similar:
                flagged.append(task)
            else:
                task["_embedding"] = embedding
                accepted.append(task)

        return accepted, flagged

    def store_batch(self, tasks: list[dict]):
        """Store accepted task embeddings in LanceDB."""
        rows = []
        for task in tasks:
            embedding = task.pop("_embedding", None)
            if embedding is None:
                continue
            rows.append({
                "task_id": task.get("task_id", ""),
                "persona_id": task.get("persona_id", ""),
                "text_fingerprint": _task_to_text(task)[:500],
                "vector": embedding,
            })

        if rows:
            self.table.add(rows)

    def find_similar(self, task: dict, top_k: int = 5) -> list[dict]:
        """Find the most similar tasks in the DB to a given task."""
        text = _task_to_text(task)
        embedding = self.embed_texts([text])[0]

        if self.table.count_rows() == 0:
            return []

        results = (
            self.table.search(embedding)
            .metric("cosine")
            .limit(top_k)
            .to_pandas()
        )

        similar = []
        for _, row in results.iterrows():
            similar.append({
                "task_id": row["task_id"],
                "persona_id": row["persona_id"],
                "similarity": round(1.0 - row["_distance"], 3),
            })
        return similar

    def get_stats(self) -> dict[str, Any]:
        """Return basic stats about the embedding store."""
        return {
            "total_embeddings": self.table.count_rows(),
            "db_path": self.db_path,
            "model": self.model,
            "threshold": self.threshold,
        }


def _cosine_similarities(query: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between a query vector and a set of vectors."""
    query_norm = query / (np.linalg.norm(query) + 1e-10)
    vectors_norm = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-10)
    return vectors_norm @ query_norm
