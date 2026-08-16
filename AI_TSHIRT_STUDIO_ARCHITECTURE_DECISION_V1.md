# AI T-Shirt Studio — Architecture Decision Record V1

**Document:** `AI_TSHIRT_STUDIO_ARCHITECTURE_DECISION_V1.md`
**Version:** 1.1 — extended at Gate 0.5 (Brand Baseline)
**Status:** Locked. Supersedes candidate selections in Technical Specification V1.0 §41.
**Date:** 2026-08-16
**Basis:** Gate 0 read-only environment and architecture audit, accepted as PASS WITH CHANGES; extended by
the Gate 0.5 Brand DNA delta review, accepted with the name-is-not-mark correction.

**Gate 0.5 additions:** evidence E6–E7; decisions **D-15**, **D-16**, **D-17**; amendments to **D-06**,
**D-09**, **D-10**. **No Gate 0 decision was reversed or weakened.**

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

### E6 — Printer statement (product owner, 2026-08-16)

The printer stated: **"PNG without background."**

Treated as confirmed evidence for **exactly two** facts: PNG is accepted/required, and a transparent
background is required.

**Nothing further is inferred from it** — not DPI, colour profile, mirroring, maximum dimensions, minimum
feature size, or transfer technology. Note that the two confirmed fields are among the *least*
consequential in the profile; every field that gates the validator remains open, so
`PRINTER_REQUIREMENTS_CHECKLIST.md` remains blocking (**D-11**).

### E7 — Brand DNA (product owner, 2026-08-16)

The creative target is merchandise for **The Incredible You**, not a generic AI T-shirt generator.

Supplied: canonical brand name; identity observations (strong uppercase typography; THE / INCREDIBLE as a
dominant typographic structure; YOU as a major visual element; red as an important brand colour; a human
figure integrated into the identity; black-on-light and white-on-coloured usages); creative territory
(motivational typography, headline-led composition, mixed type styles, bold contrast, typography with
simple illustration, occasional art-led work, black/white garments, restrained-premium through
loud-streetwear registers); and four usage tiers.

Six proprietary vocabulary terms supplied **by name only**: `Inner DNA`, `Baselines`, `N-Codes`,
`E-Codes`, `Outcomes Plus`, `Secret Millionaire Blueprint`. **Meanings were explicitly not supplied and
must not be inferred.**

Two explicit constraints recorded by the product owner:

1. Reference images are inspiration for composition and style diversity only. Supplied artwork must never
   be reproduced, traced, imitated or derived from.
2. **Screenshots are not authoritative production logo files.** The canonical brand *name* is a text
   string and is usable; the official brand *mark* requires a supplied asset file and must never be
   reconstructed from screenshots. The brand red hex is unknown and must not be sampled or estimated from
   screenshots.

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

**Amended 2026-08-16 (Gate 0.5) — IP rationale.** E7 supplies a second and stronger justification. Terms
such as `N-Codes`, `E-Codes` and `Inner DNA` are structurally hostile to image models: hyphens, internal
capitalisation and plurals are the first things diffusion text rendering degrades. `N-Codes` becomes
`N Codes`, `NCodes`, `N-Code`. That is not a typo — it is **corruption of proprietary terminology**, made
physical and permanent on merchandise. D-06 is therefore no longer only a cost control; it is an IP
control. The **D-10 amendment** makes the correctness of these strings machine-checkable.

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

**Strengthened 2026-08-16 (Gate 0.5).** E6 — the printer's "PNG without background" — confirms a raster,
transparency-consuming workflow and offers no indication of a vector requirement. D-09 rests on better
evidence than when it was taken.

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

**Amended 2026-08-16 (Gate 0.5) — canonical-string assertion.** Validation additionally asserts that
composited authoritative text **byte-matches** the `exact_spelling` recorded in Brand DNA (**D-15**).

*Why this is now possible and was not before:* Brand Vocabulary supplies an authoritative string to
compare against. Before E7 there was no canonical form to assert on, so wording correctness rested on
human proofreading. It is a pure function over two strings — no I/O, no model, negligible cost — and it
converts the highest-severity IP risk in the system (**D-06**) from a discipline into a machine check that
fails closed.

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

### D-15 — Brand DNA is versioned data, not code

**Decided.** Brand identity, creative territory and Brand Vocabulary live in a versioned data file in the
repository (`brand/the-incredible-you.json`), loaded by the brief layer. The schema carries `status` and
`source_ref` **from schema_version 1**. Ingestion is not built.

**Why decide now rather than later.** Three concrete rework risks, not convenience:

1. The structured-brief schema is already declared versioned and consumed by downstream code (spec §7).
   Adding brand fields later is a migration against existing briefs and provenance records.
2. Validation now depends on canonical strings (**D-10 amendment**) — a hard data dependency from the most
   correctness-critical module into Brand DNA.
3. Approval is a *lifecycle*, not a flag. The required workflow is
   `source → candidate → owner review → approved`. Without `status` and `source_ref` at v1, every future
   ingestion feature must retrofit approval state and provenance onto records that never had either — and
   there would be no source data to backfill from. Two fields now; an unbackfillable migration later.

**Infrastructure added: none.** One JSON file. No database, no index, no embeddings, no retrieval service,
no review UI. With six terms the vocabulary fits comfortably in context — **loading the file is the
implementation.** Any future proposal for a vector store over this data must justify itself against
**D-12**.

**Not built (deferred).** Document ingestion, candidate extraction, parsing, semantic search, review
tooling. The workflow is *documented as required* and *structurally supported*; it is not implemented.
Extracted candidates enter the same file with `status: "candidate"` and are unusable until the product
owner promotes them.

**Status semantics.** `status` approves **the term and its spelling**, not its meaning. A term may be
`approved` while `meaning` is `null`: the string is authoritative and printable, its meaning unknown.

**Revisit when.** Vocabulary outgrows what fits comfortably in context, or ingestion volume makes manual
review impractical.

---

### D-16 — Vocabulary with unknown meaning is exact but opaque

**Decided.** Where a vocabulary entry's `meaning` is `null`, the term **may be used as exact text** and set
in brand typography. It **must not drive visual metaphor, symbolism, or illustrative concept.**

**Why.** This closes a failure mode that no text rule catches. Spec §7 instructs the Creative Director to
determine "visual metaphors". Asked for a design around `N-Codes` — meaning unknown — a model will happily
produce a DNA helix, a padlock, or binary rain. **It has then invented a meaning and printed it.** No false
definition was ever typed, so **D-06** is satisfied and the term is spelled perfectly; a visual claim about
proprietary IP has nonetheless been manufactured and made physical.

Spelling a term correctly while illustrating it wrongly is arguably the worse outcome, because the result
looks authoritative.

**Consequence.** "Give me five designs around N-Codes" currently yields five *typographic* treatments of a
correctly spelled term — genuinely different in weight, scale, structure, contrast and composition. It does
not yield five interpretations of what N-Codes means. This sits comfortably with the creative territory in
E7, which is typography-dominant by nature.

**Note.** Meaning must come from product-owner material only. A model must never infer meaning, programme
ownership, relationships, approved usage or symbolism from a term's surface form.

**Revisit when.** Per term, automatically, the moment the product owner supplies `meaning`. Illustrative
territory then unlocks for that term with no code change.

---

### D-17 — Brand marks are placed assets, never generated; the name is not the mark

**Decided.** Two distinct things, never substituted for one another:

- **Canonical brand name** — the text string `THE INCREDIBLE YOU`. May be typeset as exact text in original
  merchandise compositions via deterministic typography. **Doing so is not official logo usage.**
- **Official brand mark** — a supplied authoritative asset file. Required for `usage_tier: official_logo`.
  **Placed, never generated.**

**Prohibited.** Reconstructing, tracing, redrawing, approximating or generating the official logo — from
screenshots, from descriptions, or from the `identity_observations` recorded in Brand DNA. Screenshots
demonstrate identity and creative context; **they are not authoritative production assets** (E7).

`identity_observations` exists for creative context and is explicitly **not** a reconstruction
specification. It is marked as such in the data file.

**Why.** This is **D-06**'s logic applied to marks rather than words. A model redrawing a wordmark produces
a *near-miss* — subtly wrong letterforms, proportions and spacing — which is more dangerous than an obvious
failure, because a near-miss ships. The same applies to the human-figure element of the identity.

**Current state.** `brand_mark_assets` is empty. **`official_logo` is unavailable until authoritative files
are supplied.** The other three tiers are available now.

**Revisit when.** Never as a principle. `official_logo` unblocks when assets are supplied.

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
| D-15 | Brand DNA is versioned data, not code | Vocabulary outgrows context |
| D-16 | Unknown meaning → exact text, no visual metaphor | Product owner supplies meaning (per term) |
| D-17 | Brand marks are placed assets; name ≠ mark | Never as principle; `official_logo` unblocks on assets |

**Amendments (Gate 0.5, 2026-08-16):** D-06 gains the IP rationale · D-09 strengthened by E6 · D-10 gains
the canonical-string assertion.

---

## Standing Licensing Rules

1. Public visibility on GitHub does not imply a right to use.
2. **Code licence and weights licence are distinct.** Verify both, separately.
3. For hosted providers, verify the terms governing **commercial use of generated outputs** — distinct
   from weights licensing, and the dominant question when using an API.
4. Record findings in the specification's licence register *before* adoption.

This discipline is what surfaced the BRIA blocker at Gate 0, before any code depended on it. It works;
keep it.
