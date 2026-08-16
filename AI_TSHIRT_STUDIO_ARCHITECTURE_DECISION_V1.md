# AI T-Shirt Studio — Architecture Decision Record V1

**Document:** `AI_TSHIRT_STUDIO_ARCHITECTURE_DECISION_V1.md`
**Version:** 1.0
**Status:** Locked. Supersedes candidate selections in Technical Specification V1.0 §41.
**Date:** 2026-08-16
**Basis:** Gate 0 read-only environment and architecture audit, accepted as PASS WITH CHANGES.

---

## Purpose

This record fixes the architectural decisions taken at Gate 0, the evidence behind each, and the
conditions under which each may be revisited. Its function is to stop settled questions from being
relitigated, and to make sure that when a decision *is* reversed, it is reversed on evidence.

**Reading guide.** Each decision states what was decided, why, what was rejected, and what would reverse
it. A decision without a reversal condition is a decision nobody can learn from.

---

## Evidence Base

All findings below were verified directly during Gate 0 — hardware inspected, endpoints probed, and
licence files fetched from canonical repositories. Nothing here is assumed.

### E1 — Engineering environment

| Property | Measured |
|---|---|
| Platform | Ephemeral cloud VM (Firecracker/KVM), Ubuntu 24.04.4 LTS |
| CPU / RAM | 4 vCPU Intel Xeon @ 2.10 GHz / 15 GiB, no swap |
| Disk | ~30 GB available |
| **GPU** | **None.** No `nvidia-smi`, no `/dev/nvidia*`, no `/dev/dri`, no ROCm, no VGA/3D PCI device |
| Persistence | **None.** No persistent mounts. Repo cloned fresh per session; container reclaimed on inactivity |
| Present toolchains | Python 3.11.15, Node 22, Docker, Rust, Go, Java 21, `psql` client, system fonts |
| Absent | `torch`, `diffusers`, `Pillow`, `numpy`, ImageMagick, Inkscape, `potrace`, VTracer, `ffmpeg`, `git-lfs`, ComfyUI — i.e. every proposed pipeline dependency |
| Verified installable | Pillow 12.3.0 resolves and downloads cleanly from the permitted PyPI mirror |

### E2 — Network egress

| Reachable | Blocked |
|---|---|
| PyPI, npm, crates index, Go proxy | **huggingface.co** |
| github.com, raw.githubusercontent.com | api.openai.com, api.replicate.com, fal.run, api.bfl.ai |
| Google API endpoints (`generativelanguage`, `aiplatform`) — live, no key | Stability, Ideogram, Recraft, Leonardo, Together, DeepInfra, OpenRouter, Runware, ModelsLab, Novita |
| Anthropic | Supabase (direct HTTP), Slack, Cloudflare R2 |

Of 18 image-generation API hosts probed, **one vendor's endpoints were reachable.** No AI provider API
key is present in the environment.

### E3 — Licences (fetched from canonical `LICENSE` files)

ComfyUI **GPL-3.0** · ComfyUI-RMBG **GPL-3.0** · BRIA RMBG-2.0 **CC BY-NC 4.0, commercial use requires a
paid agreement** · Qwen-Image **Apache-2.0 (code and weights)** · VTracer **MIT** · Fabric.js **MIT** ·
BiRefNet **MIT** · InSPyReNet / transparent-background **MIT** · rembg **MIT (code only; weights differ)**

### E4 — Model capability (2026 market)

Verbatim text rendering is broadly solved at the top of the image-model market. Qwen-Image's V1.0
justification — "comparatively strong text rendering" — is no longer a meaningful differentiator, and is
moot in any case under **D-06**, where the image model never renders final wording.

### E5 — Transfer-print conventions (DTF)

Transparent PNG · **RGB, not operator-converted CMYK** — the RIP performs conversion and produces better
colour from an RGB source · 300 DPI **at final print size** · **do not pre-mirror** — the RIP mirrors
automatically and a pre-mirrored file presses backwards · convert text to outlines to prevent font
substitution, cited as the most common cause of a transfer that arrives "almost right".

> These are industry conventions, not a substitute for the actual printer's answers. They inform the
> questions in `PRINTER_REQUIREMENTS_CHECKLIST.md`; the printer's replies are authoritative.

---

## Decisions

### D-01 — The print-processing core is UI-agnostic

**Decided.** The core is a library with a typed, in-process API and no knowledge of its caller. V1 ships a
thin CLI adapter. An HTTP layer and browser UI may be added later.

**Why.** The current cloud terminal is the engineering environment, **not necessarily the permanent
runtime**. Binding the core to any interface — CLI, HTTP or otherwise — would force a rewrite when the
runtime moves.

**Rejected.** Building a web application now: no route from the cloud terminal to a browser exists, and
the conversational layer already provides the V1 operating surface. Building a CLI *as* the architecture:
would embed argv and terminal assumptions in the core and produce exactly the rewrite this avoids.

**Test.** Adding a browser UI must require zero changes under `core/`.

**Revisit when.** Never as a whole. This constraint outlives every other decision here.

---

### D-02 — ComfyUI excluded from V1

**Decided.** Not a dependency.

**Why.** ComfyUI's distinctive value is its interactive node-graph GUI, which the specification already
forbids exposing to the operator. Remove the GUI and what remains is an untyped JSON graph API with
node-version drift and custom-node dependency conflicts, licensed **GPL-3.0** (E3). With local inference
out (**D-03**), it has no function whatsoever.

Specification V1.0 §8.1 justified Qwen-Image partly *because* of "integration with ComfyUI" — a
dependency justified by another dependency rather than by print outcome. Neither survives that test.

**Rejected.** Retaining ComfyUI as a future-proofing layer: it would be dead weight against a hosted API
and strictly worse than `diffusers` for any future local path.

**Revisit when.** Local self-hosted inference becomes a requirement **and** node-graph experimentation is
demonstrably needed. Even then, `diffusers` (Apache-2.0, typed, pinnable) is the preferred starting point.

---

### D-03 — Hosted image generation; no local GPU dependency

**Decided.** V1 uses hosted image generation. No V1 code may assume a GPU.

**Why.** No local GPU is a V1 requirement (product decision), and no GPU exists in the engineering
environment (E1). Time to first physical shirt is the binding constraint, not inference sovereignty.

**Rejected.** Local inference in V1 — impossible here on three independent grounds: no GPU; ~30 GB free
disk against ~40 GB of weights; and Hugging Face blocked (E1, E2).

**Revisit when.** Privacy, per-image cost, or provider availability makes self-hosting worthwhile — see
**D-04**.

---

### D-04 — Qwen-Image documented as an optional future path only

**Decided.** Not a runtime dependency. Recorded as the recommended candidate should self-hosted generation
ever be required.

**Why.** Its **Apache-2.0 licence covering both code and weights** (E3) is the most commercially
permissive of any model surveyed, and is a genuine strategic asset worth not losing. But it needs ~24 GB
VRAM quantised, 42–45 GB at full precision, and ~40 GB of weight storage — none of which V1 has or needs.
Its text-rendering advantage is additionally moot under **D-06**.

**Revisit when.** **D-03** is reversed. At that point Qwen-Image is the default candidate on licensing
grounds alone.

---

### D-05 — Provider abstraction with two implementations, one of them non-AI

**Decided.** A single `ImageProvider` interface (`generate`, `edit`) with two implementations from day
one: a hosted provider, and **`FileProvider`**, which accepts an operator-supplied image from any source.

**Why.** Exactly one hosted image vendor is currently reachable (E2). **This is a network policy fact, not
a product decision, and must not calcify into architecture.** An interface written against a single
implementation encodes that implementation's assumptions; only a second implementation proves the seam.

`FileProvider` was chosen as that second implementation because it is not a stub — it keeps the entire
deterministic print pipeline operational with zero AI availability, and is a genuine escape hatch if the
provider, the key, the egress policy, or the model changes.

**Constraints.** No provider name in `core/`. Provider selection is configuration. Adding a provider
touches only `providers/`.

**Rejected.** Deferring the abstraction until a second provider is reachable — that is how single-provider
assumptions become permanent. Including `inpaint` and `upscale` in the initial interface — unevenly
supported and unnecessary to prove the pipeline.

**Revisit when.** Egress widens, or a second provider becomes reachable. The interface should absorb it
without core changes; if it does not, the abstraction failed and must be corrected.

---

### D-06 — AI-rendered wording never enters a production print asset

**Decided.** Where wording matters, the image model produces the **graphic** only. Final text is
composited deterministically from a pinned font file. Any model-rendered text is disposable placeholder.

**Why.** A wording error is discovered *after* a transfer has been paid for and pressed — the most
expensive possible place to find a typo. Print shops independently require text converted to outlines,
because font substitution is the most common cause of a transfer arriving "almost right" (E5); a
deterministic raster composite satisfies this by construction.

This is also **cheaper**: it removes prompt-retry loops chasing correct glyphs, makes wording changes a
free re-render, and eliminates a whole validation burden.

**Consequence.** Deterministic typography compositing is **core to Gate 1**, not deferred with the rest of
the UI.

**Rejected.** Specification V1.0's softer "should support recreating or overlaying" — it permits the
failure it was written to prevent.

**Revisit when.** Never. This is the single highest-value rule in the specification.

---

### D-07 — Single rendering path

**Decided.** Text and artwork compositing happen in exactly one place: the core, driven by a declarative
layout object. The V1 conversational workflow edits that object; a future browser editor manipulates the
same object and calls the same function.

**Why.** A UI that composites differently from the export path is the classic mechanism by which previews
come to disagree with prints — and the disagreement surfaces on physical film.

**Revisit when.** Never.

---

### D-08 — Deterministic keying first for transparency; BRIA prohibited

**Decided.** Deterministic background keying is the primary method. Permissively licensed segmentation
(**BiRefNet** or **InSPyReNet**, both MIT — E3) is the fallback for photographic or complex artwork.
**BRIA RMBG-2.0 and derivatives are prohibited.**

**Why — licence.** RMBG-2.0 is **CC BY-NC 4.0; commercial use requires a paid agreement with BRIA** (E3).
Selling T-shirts is commercial use. It sat in Specification V1.0's candidate table as a recommended
component and is a genuine legal blocker. ComfyUI-RMBG additionally carries GPL-3.0.

**Why — technical.** For the flat, limited-palette streetwear graphics this product targets, segmentation
is often the wrong instrument. Generating on a flat uniform background and keying deterministically is
faster, GPU-free, licence-free, and — decisively — **predictable**. Predictability outranks sophistication
when the output goes to film.

**Revisit when.** Gate 1 shows deterministic keying inadequate for the actual artwork style. The fallback
is already selected and licence-cleared.

---

### D-09 — Vectorization deferred; V1 is raster-only

**Decided.** V1 produces transparent raster PNG only. No VTracer, no classifier, no quality-guard, no
raster/vector decision engine.

**Why.** DTF consumes transparent raster PNG at final size (E5). Vector output has no confirmed consumer
in the stated pipeline (transfer printer → heat press). Vectorization genuinely matters for screen
printing, vinyl cutting and embroidery — none currently in scope.

Specification V1.0 §13 specified a full subsystem — classifier, tracer, quality-regression guard covering
"colour changes, contour errors, excessive paths, visual degradation, lost detail", plus fallback logic —
to produce an artifact the printer likely will not accept. **This is the largest single scope reduction
taken at Gate 0.**

**Rejected.** Building it "in case" — the quality guard alone is hard to make reliable, and would be built
against no known consumer.

**Revisit when.** `PRINTER_REQUIREMENTS_CHECKLIST.md` returns a vector format as accepted or preferred, or
scope extends to screen printing, vinyl or embroidery. VTracer (MIT, E3) is then the starting candidate.

---

### D-10 — Validation extended to print physics

**Decided.** Beyond file/geometry checks, validation adds **alpha quality**, **minimum feature/stroke
size**, and **rendered bounds**.

**Why.** Specification V1.0 validated *file properties*. Physical prints fail on *ink and material
physics*:

- **Alpha quality** — V1.0 checked that alpha existed, never that it was clean. Soft shadows, glows and
  gradients-to-transparent print as haze or film residue over a DTF white underbase. This is the failure
  mode that looks premium on screen and ruins a shirt.
- **Minimum feature size** — detail below the printer's reliable threshold does not transfer. This single
  check is worth more than the entire vectorization subsystem removed in **D-09**.
- **Rendered bounds** — comparing actual inked extents against declared physical size catches silent
  rescaling before it reaches film.

**Thresholds come from measured Gate 1 calibration data**, never from assumption.

**Revisit when.** Calibration or production experience reveals further physical failure modes. Expect this
list to grow — that growth is the system learning.

---

### D-11 — Printer profile is a Gate 1 input, not a Gate 3 deliverable

**Decided.** A populated printer profile, sourced from the real printer, is a **precondition for physical
production**. All fields initialise to `null`; `null` is never treated as a default.

**Why.** Specification V1.0 correctly required profiles be built from real printer requirements, then
scheduled that work in Gate 3 — after the pipeline it constrains. Every downstream calculation (required
DPI, colour space, mirroring, minimum stroke, maximum dimensions) depends on these answers.

V1.0 also shipped plausible-but-hazardous example defaults: `mirror_output: false` and
`colour_space_notes: null`. Standard practice is that the **RIP** mirrors and that **RGB** is preferred
(E5). A schema that answers these questions instead of forcing them costs physical transfers.

**Revisit when.** Never. Additional printers get additional profiles.

---

### D-12 — No queue, no database server, no microservices

**Decided.** Single process, synchronous execution with progress reporting. File-backed manifest (JSON or
SQLite). Filesystem assets behind an `AssetStore` interface. No Redis, Celery, PostgreSQL, broker or
container orchestration.

**Why.** Single-user personal tool. A job queue for one operator watching the run is ceremony that creates
the duplicate-approved-revision bug class Specification V1.0 §25 itself warned about. Together with
**D-09**, this is the difference between a weeks-long build and a months-long one.

**Rejected.** PostgreSQL and the 8-entity relational model — disproportionate, and the `AssetStore` /
manifest interfaces preserve the migration path.

**Revisit when.** Genuine concurrency, multi-user access, or long-running unattended batch work appears.
Not before.

---

### D-13 — Durability is a gate requirement

**Decided.** No gate is complete until its evidence exists **outside** the engineering environment —
pushed to the repository, delivered to the operator, or exported to durable storage.

**Why.** The environment has **no persistent storage** and is reclaimed on inactivity (E1). `git-lfs` is
not installed. Specification V1.0 §24's assumption that "local storage may be acceptable" for a
single-user V1 is false here: there is no local storage. Artifacts not exported are destroyed, silently.

**Revisit when.** The runtime moves to a host with real persistence. The rule costs nothing to keep.

---

### D-14 — Python; deterministic core is I/O-free

**Decided.** Python. `core/size/` and `core/validate/` perform no I/O — values in, values out.

**Why.** The pipeline is image processing; Pillow/numpy is the mature ecosystem; Python is present and
Pillow verified installable (E1). A second runtime would add cost for no gain. Isolating the pure logic
makes the code that must never be wrong exhaustively testable at near-zero cost — roughly a few hundred
lines carrying the project's entire correctness burden.

**Revisit when.** Never for the core. UI layers may use any technology, since **D-01** keeps them outside.

---

## Decision Index

| ID | Decision | Reversal trigger |
|---|---|---|
| D-01 | UI-agnostic core | None |
| D-02 | No ComfyUI | Local inference + proven need for graph experimentation |
| D-03 | Hosted generation, no GPU | Privacy/cost/availability pressure |
| D-04 | Qwen-Image documented only | D-03 reversed |
| D-05 | Provider abstraction + `FileProvider` | Second provider reachable |
| D-06 | AI never renders final wording | None |
| D-07 | Single rendering path | None |
| D-08 | Deterministic keying; BRIA prohibited | Keying inadequate in Gate 1 |
| D-09 | Raster only, no vectorization | Printer requires vector, or new print process |
| D-10 | Print-physics validation | New physical failure modes discovered |
| D-11 | Printer profile precedes production | None |
| D-12 | No queue/DB server/microservices | Real concurrency or multi-user need |
| D-13 | Durable evidence per gate | Persistent runtime adopted |
| D-14 | Python, I/O-free core | None for the core |

---

## Standing Licensing Rules

1. Public visibility on GitHub does not imply a right to use.
2. **Code licence and weights licence are distinct.** Verify both, separately.
3. For hosted providers, verify the terms governing **commercial use of generated outputs** — distinct
   from weights licensing, and the dominant question when using an API.
4. Record findings in the specification's licence register *before* adoption.

This discipline is what surfaced the BRIA blocker at Gate 0, before any code depended on it. It works;
keep it.
