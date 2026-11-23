"""Append-only provenance log for every model call."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ProvenanceRecord:
    """One model call for copyright / authorship documentation."""

    timestamp: str
    stage: str
    model: str
    temperature: float
    prompt_hash: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    output: str
    system_hash: str = ""
    finish_reason: Optional[str] = None


def hash_text(text: str) -> str:
    """Return SHA-256 hex digest of text."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


class ProvenanceLog:
    """JSONL provenance writer/reader for a story folder."""

    def __init__(self, path: Path) -> None:
        """Initialize with path to provenance.jsonl."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        *,
        stage: str,
        model: str,
        temperature: float,
        system: str,
        prompt: str,
        output: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        finish_reason: Optional[str] = None,
    ) -> ProvenanceRecord:
        """Append one provenance line.

        Args:
            stage: Pipeline stage.
            model: Model slug.
            temperature: Sampling temperature.
            system: System prompt (hashed, not stored raw to keep file smaller).
            prompt: User prompt (hashed).
            output: Model output text (stored for authorship baseline).
            prompt_tokens: Input tokens.
            completion_tokens: Output tokens.
            cost_usd: Estimated dollar cost.
            finish_reason: Provider finish reason.

        Returns:
            The written record.
        """
        record = ProvenanceRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage=stage,
            model=model,
            temperature=temperature,
            prompt_hash=hash_text(prompt),
            system_hash=hash_text(system),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            output=output,
            finish_reason=finish_reason,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        return record

    def read_all(self) -> List[Dict[str, Any]]:
        """Load all provenance records as dicts."""
        if not self.path.exists():
            return []
        records: List[Dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def latest_output_for_stage(self, stage: str) -> Optional[str]:
        """Return the most recent model output for a stage, if any."""
        matches = [r for r in self.read_all() if r.get("stage") == stage]
        if not matches:
            return None
        return matches[-1].get("output")
