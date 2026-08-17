"""Printer profile loading, with explicit confirmed / assumed / unknown status.

A profile field is never a bare value. It carries where the value came from, so
that a conventional working baseline can never be mistaken for something the
printer actually said (D-11).

Three statuses, and the distinction is load-bearing:

  confirmed  the printer stated it
  assumed    conventional DTF baseline adopted for the calibration experiment only
  unknown    not supplied and not invented; dependent checks report PENDING
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIRMED = "confirmed"
ASSUMED = "assumed"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class Field:
    name: str
    value: Any
    status: str
    source: str | None = None
    confirm_via: str | None = None

    @property
    def is_known(self) -> bool:
        """True when a value exists to check against, whether stated or assumed."""
        return self.status in (CONFIRMED, ASSUMED) and self.value is not None


@dataclass(frozen=True)
class PrinterProfile:
    name: str
    fields: dict[str, Field]
    path: Path | None = None

    def get(self, name: str) -> Field:
        if name not in self.fields:
            return Field(name=name, value=None, status=UNKNOWN)
        return self.fields[name]

    def value(self, name: str) -> Any:
        return self.get(name).value

    def assumptions(self) -> list[Field]:
        """Every field awaiting physical confirmation."""
        return [f for f in self.fields.values() if f.status == ASSUMED]

    def unknowns(self) -> list[Field]:
        return [f for f in self.fields.values() if f.status == UNKNOWN]

    def confirmed(self) -> list[Field]:
        return [f for f in self.fields.values() if f.status == CONFIRMED]


def load_profile(path: str | Path) -> PrinterProfile:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    fields = {
        name: Field(
            name=name,
            value=spec.get("value"),
            status=spec.get("status", UNKNOWN),
            source=spec.get("source"),
            confirm_via=spec.get("confirm_via"),
        )
        for name, spec in raw["fields"].items()
    }
    return PrinterProfile(name=raw["name"], fields=fields, path=path)
