"""Hugging Face dataset loader."""

from __future__ import annotations

import logging
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)


def load_raw_rows(dataset_id: str) -> Iterator[dict[str, Any]]:
    """Stream rows from the Hugging Face dataset."""
    from datasets import load_dataset

    logger.info("Downloading dataset from Hugging Face: %s", dataset_id)
    dataset = load_dataset(dataset_id, split="train", streaming=True)
    for row in dataset:
        yield dict(row)


def load_raw_rows_list(dataset_id: str, limit: Optional[int] = None) -> list[dict[str, Any]]:
    """Materialize dataset rows (optional limit for tests)."""
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(load_raw_rows(dataset_id)):
        if limit is not None and index >= limit:
            break
        rows.append(row)
    return rows
