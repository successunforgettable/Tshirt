# AI T-Shirt Studio

Personal production tool turning a design idea into printer-ready artwork for DTF transfer
and heat press. **Physical print quality is the acceptance criterion, not screen quality.**

| Document | Purpose |
|---|---|
| `AI_TSHIRT_STUDIO_TECHNICAL_SPEC_V1.md` | Specification (v1.2) |
| `AI_TSHIRT_STUDIO_ARCHITECTURE_DECISION_V1.md` | Locked decisions D-01…D-17 with evidence |
| `GATE_1_PHYSICAL_PIPELINE_PLAN.md` | Physical proof plan |
| `GATE_1A_PHYSICAL_INSPECTION.md` | Measurement record — complete after pressing |
| `PRINTER_REQUIREMENTS_CHECKLIST.md` | Printer questionnaire |
| `brand/the-incredible-you.json` | Brand DNA (data, not code) |
| `profiles/dtf-printer-a.json` | Printer profile with confirmed/assumed/unknown status |

## Gate status

**Gate 1a: SOFTWARE READY — AWAITING PHYSICAL VALIDATION.**
Not PASS until a transfer has been printed, pressed and measured.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Two dependencies: Pillow (HPND) and numpy (BSD-3). No API keys, no GPU, no services, no
database. Gate 1a uses **no AI generation at all** — the artwork is composed
deterministically, which keeps the first physical experiment measuring the *printer*
rather than a model.

## Build

```bash
.venv/bin/python -m tshirt.cli.main build
```

Writes `output/INCREDIBLE-YOU-001/` — two print-ready PNGs, a human-readable print spec,
a manifest with checksums, and a validation report. Exits non-zero if validation fails.

## Test

```bash
.venv/bin/python -m unittest discover -s tests
```

## Architecture

```
tshirt/
├── core/          UI-agnostic, framework-free, no network  (D-01)
│   ├── size/      mm ⇄ px ⇄ effective DPI          — pure, no I/O
│   ├── validate/  PASS / WARNING / FAIL / PENDING  — pure, no I/O
│   ├── analysis/  alpha, stroke and bounds measurement
│   ├── compose/   deterministic typography         (D-06, D-07)
│   ├── profile/   printer profile with field status
│   └── package/   export tree, checksums, print spec
├── calibration/   measurement sheet generator
├── brand/         Brand DNA loader                 (D-15)
├── providers/     ImageProvider protocol + FileProvider (D-05)
└── cli/           thin adapter — the only entry point
```

`core/size` and `core/validate` perform no I/O. They carry the correctness burden and are
tested exhaustively. Adding an HTTP layer or browser UI later replaces `cli/` and nothing
underneath it.

## Rules the code enforces

- **AI-rendered wording never enters a production asset** (D-06). Final text is composited
  from a pinned OFL-licensed font and byte-matched against Brand DNA before export.
- **Unknown tolerances are never invented** (D-11). A check with no supplied threshold
  reports `PENDING`, which is not a pass. The calibration transfer is what turns those
  into real thresholds.
- **Proprietary vocabulary stays semantically opaque** (D-16). Terms with `meaning: null`
  may be set as exact text but must never drive visual metaphor.
- **Brand marks are placed assets, never generated** (D-17). The canonical brand *name* is
  a usable string; the *mark* is a file, and none has been supplied.

## Fonts

`assets/fonts/LiberationSans-Bold.ttf` — **SIL OFL 1.1**, vendored with its licence so
builds are reproducible from this repository alone. Swapping in a purchased display face
later is a one-line change to the layout, with no code change.
