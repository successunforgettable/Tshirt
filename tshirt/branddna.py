"""Brand DNA loader.

Brand DNA is versioned data, not code (D-15). This module reads it and enforces
the two rules that make it safe to consume:

  * `meaning: null` means UNKNOWN. The loader never fills it in, and exposes
    `is_opaque` so callers can honour D-16 — such a term may be set as exact
    text but must never drive visual metaphor.
  * The canonical brand NAME is a string and is usable. The brand MARK is a file
    and must be supplied. They are different things (D-17).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "brand" / "the-incredible-you.json"


@dataclass(frozen=True)
class VocabularyEntry:
    id: str
    canonical_name: str
    exact_spelling: str
    capitalisation: str | None
    status: str
    meaning: str | None
    programme: str | None
    related_terms: list[str]
    approved_usage: str | None
    restricted_usage: str | None

    @property
    def is_approved(self) -> bool:
        """Approval covers the term and its spelling, never its meaning."""
        return self.status == "approved"

    @property
    def is_opaque(self) -> bool:
        """True when meaning is unknown: usable as exact text, no visual metaphor."""
        return self.meaning is None


@dataclass(frozen=True)
class BrandDNA:
    brand: str
    canonical_brand_name: str
    brand_mark_assets: list[str]
    usage_tiers: dict[str, dict[str, Any]]
    colours: list[dict[str, Any]]
    creative_territory: dict[str, Any]
    vocabulary: dict[str, VocabularyEntry]
    path: Path

    def term(self, term_id: str) -> VocabularyEntry:
        if term_id not in self.vocabulary:
            raise KeyError(f"Unknown vocabulary term: {term_id!r}")
        return self.vocabulary[term_id]

    def exact_spelling(self, term_id: str) -> str:
        return self.term(term_id).exact_spelling

    @property
    def opaque_terms(self) -> list[VocabularyEntry]:
        """Approved terms whose meaning has not been supplied (D-16 applies)."""
        return [e for e in self.vocabulary.values() if e.is_approved and e.is_opaque]

    @property
    def official_logo_available(self) -> bool:
        """official_logo usage requires a supplied authoritative asset (D-17)."""
        return bool(self.brand_mark_assets)

    def colour_hex(self, name: str) -> str | None:
        for c in self.colours:
            if c.get("name") == name:
                return c.get("hex")
        return None

    def authoritative_strings(self, term_ids: list[str], include_brand_name: bool = False) -> list[str]:
        out = [self.exact_spelling(t) for t in term_ids]
        if include_brand_name:
            out.insert(0, self.canonical_brand_name)
        return out


def load_brand_dna(path: str | Path | None = None) -> BrandDNA:
    path = Path(path) if path else DEFAULT_PATH
    raw = json.loads(path.read_text(encoding="utf-8"))
    identity = raw["identity"]

    vocab = {
        e["id"]: VocabularyEntry(
            id=e["id"],
            canonical_name=e["canonical_name"],
            exact_spelling=e["exact_spelling"],
            capitalisation=e.get("capitalisation"),
            status=e.get("status", "candidate"),
            meaning=e.get("meaning"),
            programme=e.get("programme"),
            related_terms=e.get("related_terms", []),
            approved_usage=e.get("approved_usage"),
            restricted_usage=e.get("restricted_usage"),
        )
        for e in raw["vocabulary"]
    }

    return BrandDNA(
        brand=raw["brand"],
        canonical_brand_name=identity["canonical_brand_name"],
        brand_mark_assets=identity.get("brand_mark_assets", []),
        usage_tiers={t["id"]: t for t in identity.get("usage_tiers", [])},
        colours=identity.get("colours", []),
        creative_territory=raw.get("creative_territory", {}),
        vocabulary=vocab,
        path=path,
    )
