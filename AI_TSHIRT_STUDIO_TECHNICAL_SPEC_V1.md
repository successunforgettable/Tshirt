# AI T-Shirt Studio — Technical Specification V1

**Document:** `AI_TSHIRT_STUDIO_TECHNICAL_SPEC_V1.md`
**Version:** 1.1 — revised at Gate 0
**Status:** Accepted baseline. Supersedes V1.0.
**Date:** 2026-08-16
**Supersedes:** V1.0 (2026-08-16), reviewed and accepted as PASS WITH CHANGES.

> **Companion documents**
> - `AI_TSHIRT_STUDIO_ARCHITECTURE_DECISION_V1.md` — locked decisions and their evidence
> - `GATE_1_PHYSICAL_PIPELINE_PLAN.md` — the physical proof experiment
> - `PRINTER_REQUIREMENTS_CHECKLIST.md` — blocking input for Gate 1

---

## 0. Revision Summary — What Changed at Gate 0

V1.0 was reviewed against the real engineering environment. The product intent survived intact. The
implementation stack did not. Every change below is traceable to verified evidence recorded in the
architecture decision record.

### Removed

| Removed from V1 | Reason |
|---|---|
| ComfyUI | Its unique value is an interactive node GUI that V1.0 §39.1 already forbade exposing. Stripped of the GUI it is an untyped JSON graph API with version drift, under GPL-3.0. Nothing remained that justified it. |
| Qwen-Image as a runtime dependency | Requires a 24–45 GB VRAM GPU. No local GPU is a V1 requirement. Retained as a documented optional self-hosted path only (§8.5). |
| ComfyUI-RMBG / BRIA RMBG-2.0 | RMBG-2.0 is CC BY-NC 4.0; commercial use requires a paid BRIA agreement. Selling shirts is commercial use. Hard blocker. |
| VTracer and the raster/vector decision engine | DTF consumes transparent raster PNG. Vector output has no confirmed consumer. Deferred until a printer requirement proves otherwise. |
| Redis / Celery / job queue / workers | Single user, single operator. A queue for one person creates the duplicate-revision bug class that V1.0 §25 warned about, and solves nothing. |
| PostgreSQL and the 8-entity relational model | Disproportionate to a single-user tool. Replaced by a file-backed manifest. |
| Collections | Deferred to Gate 4. Not required to prove the physical pipeline. |
| Library filter matrix, PDF spec-sheet generation | Deferred. A plain-text print spec carries identical information. |

### Added

| Added | Reason |
|---|---|
| Alpha-quality validation | Presence of an alpha channel was validated; its *quality* was not. Partial alpha, glows and soft edges print as haze over a DTF white underbase. This is a leading cause of print failure and was unspecified. |
| Minimum feature / stroke-size validation | Detail below the printer's reliable threshold does not transfer. Worth more than the entire vectorization subsystem it replaces. |
| Rendered-bounds validation | Verifies actual inked pixel extents against the declared physical size, catching silent scaling errors. |
| `FileProvider` — a real non-AI input path | Makes the deterministic print pipeline usable with zero AI availability, and is the second implementation that proves the provider seam is real. |
| Durable evidence export | The current engineering environment is ephemeral. Artifacts not pushed or exported are destroyed. |
| Explicit runtime/deployment separation (§3) | V1.0 conflated the engineering environment with the product's runtime. |

### Hardened

- **Typography.** V1.0 §10.1 said the system *should support* recreating text. This is now absolute:
  AI-rendered wording must never enter a production print asset (§10).
- **Printer profile.** V1.0 treated it as a Gate 3 deliverable. It is a **Gate 1 input** and blocks
  physical production (§15).
- **Provider replaceability.** More important now, not less: only one hosted provider is currently
  reachable from the engineering environment. That is a network fact, not a product decision, and must
  not be hard-coded (§8).

---

## 1. Product Definition

AI T-Shirt Studio is a personal/internal production tool that turns a design idea or visual reference
into professional T-shirt artwork that can be refined, validated for physical printing, and exported as
a printer-ready package.

It is **not** a general-purpose image generator, a Photoshop replacement, an e-commerce platform, a
print-on-demand marketplace, or a manufacturing-management system.

**Primary workflow**

```
Idea → Design Brief → Artwork → Refine → Deterministic Typography
     → Transparency → Physical Sizing → Validation → Printer Package
     → Transfer Printer → Heat Press → Physical Inspection
```

The system must hide AI and graphics-engine complexity from the operator.

---

## 2. Objectives

### 2.1 Primary

Allow a non-technical operator to produce physically printable T-shirt designs without needing to
understand diffusion models, prompts, samplers, checkpoints, LoRAs, vector tracing, DPI calculations,
alpha channels, or print-area mathematics.

### 2.2 Secondary

1. Generate multiple genuinely different creative directions.
2. Support conversational refinement.
3. Preserve design history non-destructively.
4. Handle typography with absolute reliability.
5. Produce true transparent artwork.
6. Create correctly sized print assets from physical dimensions.
7. Validate deterministically against a real printer profile.
8. Generate garment previews for approval.
9. Package artwork and instructions for the transfer printer.
10. Preserve approved designs durably.

---

## 3. Deployment and Runtime Model

> This section is new in V1.1. V1.0 did not distinguish these, and the distinction drives §4.

### 3.1 Engineering environment (current)

Claude Code executing in a cloud terminal. Verified characteristics:

- Ephemeral. Reclaimed on inactivity; the repository is cloned fresh each session.
- No persistent volume. **Only committed and exported artifacts survive.**
- Restricted egress. Package registries and Google API endpoints are reachable; most third-party AI
  and storage vendors are not.
- No GPU.

### 3.2 Runtime environment (not yet fixed)

**The engineering environment is explicitly not assumed to be the permanent runtime.** V1 optimises for
the fastest personal-use workflow, but the product must remain relocatable to a workstation, a small
server, or a container host without redesign.

### 3.3 Consequence — the core must be interface-agnostic

The print-processing core is a **library with a typed, in-process API**. It has no knowledge of how it
is invoked.

```
        ┌─────────────┐   ┌──────────────┐   ┌───────────────┐
        │ CLI (V1)    │   │ HTTP (later) │   │ Browser UI    │
        └──────┬──────┘   └──────┬───────┘   └───────┬───────┘
               └─────────────────┼───────────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │  print-processing core │   ← no I/O assumptions,
                    │  (pure library API)    │     no framework, no UI
                    └────────────────────────┘
```

**Rule:** adding a browser UI later must require *zero changes* to the core. Any core function that
prints to a terminal, reads argv, or assumes a filesystem layout violates this and is a defect.

---

## 4. Architecture

### 4.1 Component map

```
tshirt/
├── core/                        ← UI-agnostic, framework-free, no network
│   ├── size/          mm ⇄ px ⇄ effective DPI            (pure)
│   ├── validate/      PASS / WARNING / FAIL              (pure)
│   ├── compose/       artwork + deterministic typography
│   ├── alpha/         deterministic keying; model fallback
│   ├── mockup/        flat composite onto garment photo
│   └── package/       export tree + manifest + checksums
│
├── providers/                   ← replaceable, behind one interface
│   ├── base.py        ImageProvider protocol
│   ├── hosted.py      hosted API implementation
│   └── file.py        FileProvider — non-AI input path
│
├── brief/             structured brief generation (LLM-backed)
├── store/             manifest + asset store behind an interface
└── cli/               thin adapter over core/  ← the only V1 entry point
```

**Deliberately absent from V1:** web server, database server, job queue, message broker, container
orchestration, ComfyUI, vectorizer, GPU dependency, microservices.

### 4.2 Language

Python. The pipeline is fundamentally image processing (Pillow/numpy); Python is present in the
engineering environment; and the deterministic core is the part that most benefits from a mature
imaging ecosystem. A second runtime would be added cost for no gain.

### 4.3 Purity boundary

`core/size/` and `core/validate/` perform **no I/O**. They accept values and return values. This is the
code that must never be wrong, and it is also the cheapest code to test exhaustively. Everything else
may touch the filesystem or network.

---

## 5. Operating Experience

V1 is operated conversationally through Claude Code plus deterministic scripts. The four product stages
are commands, not screens:

| Stage | V1 form | Later form |
|---|---|---|
| Create | command + structured brief | browser screen |
| Refine | conversational instruction → re-run | browser screen |
| Mockup | generated composite image, reviewed inline | interactive placement |
| Print | validate → package → export | browser screen |

The conversational layer is genuine product surface, not a placeholder. It is replaced by a UI when a UI
earns its place — not before.

---

## 6. Create Workflow

### 6.1 Input

Natural-language description; garment colour; garment style and size; print location; **exact wording**
(verbatim, treated as authoritative); optional reference images; optional style references.

### 6.2 Structured brief

Raw user language must never be passed blindly to the image model as the complete generation strategy.
It is first converted to a structured brief:

```json
{
  "concept": "Mind Hacker",
  "message": "MIND HACKER",
  "message_is_authoritative": true,
  "garment": { "type": "oversized_tshirt", "colour": "black", "size": "L" },
  "placement": "large_back",
  "aesthetic": ["premium streetwear", "futuristic", "sophisticated"],
  "palette": ["white", "electric blue"],
  "typography_role": "dominant",
  "graphic_complexity": "medium",
  "creative_directions": 4
}
```

`message_is_authoritative: true` binds the pipeline to §10: that wording is rendered by the typography
engine, never by the image model.

---

## 7. Design Director

An LLM-backed reasoning layer translating intent into coherent visual directions. It determines dominant
message, hierarchy, composition, typography role, visual metaphors, garment constraints, colour strategy,
print-technique implications, and whether the design is typography-led, illustration-led, or photographic.

**Multiple directions** must be meaningfully different — distinct creative strategies, not four seeds of
one prompt. Each carries its own generation brief.

**In V1** this role is performed conversationally. The structured-brief *schema* is fixed and versioned
regardless, because downstream code consumes it.

**The LLM provider must be replaceable.** Business logic must not couple to a single vendor.

---

## 8. Image Generation

### 8.1 Provider interface

```
generate(brief)               → image
edit(image, instruction)      → image
```

`inpaint` and `upscale` are **not** in the V1 interface. They are unevenly supported across providers and
unnecessary to prove the pipeline. Add them when a real need appears.

### 8.2 Required implementations

Two, from day one:

1. **Hosted provider** — the primary generation path.
2. **`FileProvider`** — accepts an image supplied by the operator from any source.

`FileProvider` is not a test stub. It is a first-class path that keeps the entire deterministic print
pipeline operational with zero AI availability, and it is the second implementation that proves the
abstraction is real rather than aspirational.

### 8.3 Provider neutrality

At the time of the Gate 0 audit, exactly one hosted image provider was reachable from the engineering
environment. **This is a network policy fact, not a product decision.**

- No provider name may appear in `core/`.
- Provider selection is configuration, not code.
- Provider-specific request/response shaping lives only in that provider's module.
- Adding a provider must require no change outside `providers/`.

### 8.4 Model selection is evidence-driven

The correct model is the one that produces the best *physical print*, established by testing. Screen
quality is not the criterion.

### 8.5 Optional future self-hosted path (documented, not built)

Should sovereign or offline generation ever be required, **Qwen-Image** is the recommended candidate: it
is Apache-2.0 for both code and weights — the most commercially permissive option surveyed — and is
therefore free of the licence risk that affects several alternatives.

It requires roughly 24 GB VRAM quantised and 42–45 GB at full precision, plus ~40 GB of weight storage.
**It is not a V1 dependency and no V1 code may assume it.** Recorded here so the option is not lost.

---

## 9. Refinement and Revisions

A selected design is a branch of revisions:

```
Design 003
 ├── Revision 1
 ├── Revision 2
 └── Revision 3  ← selected
```

The system records, per revision: source revision, instruction, structured brief, provider, model,
pipeline version, seed/config where applicable, input asset, output asset, timestamp, approval status.

**Non-destructive revision history is a core product requirement.** Generation failure must never destroy
a previously approved revision, and refinement operates *from* a selected revision rather than replacing
history.

**V1 scope:** the *recording* obligation applies from the first script that produces an asset — provenance
is cheap to write and impossible to reconstruct later. Rich revision-tree navigation is Gate 2.

---

## 10. Typography — Hard Rule

Typography is the highest-severity production risk, because a wording error is discovered only after a
transfer has been paid for and pressed.

> ### **AI-rendered wording must never enter a final production print asset.**
>
> Where wording matters, the image model generates the **graphic**. Final text is composited
> deterministically from a font file by the typography engine. Any text produced by the image model is
> disposable placeholder and must be removed or covered before export.

This is also the *cheaper* path: it eliminates prompt-retry loops chasing correct glyphs, makes wording
changes a free re-render, and removes an entire validation burden.

Print shops independently require text converted to outlines to prevent font substitution — a rasterised
deterministic composite satisfies this by construction.

### 10.1 Typography layer

Minimum controls: text content, font (explicit file, version-pinned), size, weight, tracking, line height,
alignment, rotation, colour, position, scale. Curve/distortion support may come later.

### 10.2 Rendering path

Text is composited by the **core**, driven by a declarative layout object. The V1 operator edits that
layout conversationally; a later browser editor manipulates the same object and calls the same core
function. **There is exactly one rendering path.** A UI that composites differently from the export path
is how previews come to disagree with prints.

---

## 11. Transparency

Production artwork requires a true alpha channel.

### 11.1 Deterministic keying first

Preferred method: generate artwork on a **flat, uniform, high-contrast background** and remove it
deterministically (luma/chroma threshold with controlled edge refinement).

For flat, limited-palette streetwear graphics this is faster than segmentation, has no model licence
exposure, no GPU cost, and — decisively — is **predictable**. Predictability matters more than
sophistication when the output goes to a printer.

### 11.2 Fallback

Where deterministic keying is inadequate (photographic or complex artwork), use a **commercially safe,
permissively licensed** segmentation model. Candidates verified as MIT-licensed at Gate 0: **BiRefNet**,
**InSPyReNet / `transparent-background`**.

**Prohibited:** BRIA RMBG-2.0 and any derivative, on licence grounds (§18).

For any model-based tool, the *code* licence and the *weights* licence must both be verified — they
frequently differ.

### 11.3 Output requirements

True alpha channel; no accidental solid background; minimal haloing; preserved edge detail; and
**alpha quality** conforming to §16.2.

---

## 12. Physical Sizing and Resolution

The system reasons in **physical dimensions**. Pixels are derived, never assumed.

- Canonical internal unit: **millimetres**. Inches are an input/display convenience.
- Effective DPI is **computed**, never read from image metadata:

```
effective_dpi = pixel_width / (physical_width_mm / 25.4)
```

- Required pixel dimensions are **derived** from the target physical size and the profile's required DPI:

```
required_px = ceil((physical_mm / 25.4) * required_dpi)
```

Worked example: a 280 mm back print at 300 DPI requires **3307 px** wide.

Upscaling is conditional, applied only when the computed requirement is unmet, and the upscaler must be
replaceable.

---

## 13. Raster vs Vector — Deferred

**V1 produces transparent raster PNG only.**

Rationale: DTF and comparable transfer processes consume transparent raster PNG built at final size.
Vector output has no confirmed consumer in the stated pipeline (transfer printer → heat press).
Vectorization is genuinely required for screen printing, vinyl cutting and embroidery — none of which are
currently in scope.

**Reinstatement trigger:** a printer requirement (§15, captured via
`PRINTER_REQUIREMENTS_CHECKLIST.md`) that names a vector format as accepted or preferred. At that point
VTracer (verified MIT at Gate 0) is the recommended starting candidate, together with the quality-guard
and raster-fallback logic from V1.0 §13.4.

Until then this subsystem is not built.

---

## 14. Printer Profiles

Printer requirements must never be hard-coded. A profile describes one supplier and process.

```json
{
  "name": "",
  "process": "",
  "accepted_formats": [],
  "preferred_format": "",
  "required_dpi": null,
  "colour_space": null,
  "max_width_mm": null,
  "max_height_mm": null,
  "requires_transparency": null,
  "white_underbase_behaviour": "",
  "rip_handles_mirroring": null,
  "min_reliable_stroke_mm": null,
  "printer_resizes_files": null,
  "cutting_responsibility": "",
  "cost_per_transfer": null,
  "turnaround": "",
  "special_instructions": "",
  "source": "supplied by printer on <date>",
  "custom_requirements": {}
}
```

### 14.1 No invented defaults

Every field above initialises to `null` or empty. **A field whose value has not been supplied by the real
printer is `null`, and `null` is never treated as a default.**

V1.0 shipped plausible-but-hazardous defaults — `mirror_output: false` and `colour_space_notes: null` —
in a schema example. Standard transfer practice is that the **RIP** handles mirroring and that **RGB** is
preferred over operator-converted CMYK. A pre-mirrored file presses backwards and a wrongly converted
colour space degrades output. These are exactly the errors that cost physical transfers, so the schema
must force the question rather than answer it.

`custom_requirements` accommodates supplier-specific requirements not anticipated here.

### 14.2 Profile precedes production

**A populated printer profile is a precondition for physical production in Gate 1.** No transfer is
ordered against assumptions.

---

## 15. Validation

Deterministic checks run before any export is declared print-ready. Every check returns
**PASS**, **WARNING**, or **FAIL**. A FAIL blocks print-ready status unless explicitly overridden, and the
override is recorded.

### 15.1 File and geometry

- File format against `accepted_formats`
- Pixel dimensions present and non-degenerate
- Declared physical dimensions present
- **Effective DPI** ≥ `required_dpi` (computed, §12)
- Physical dimensions within `max_width_mm` / `max_height_mm`
- Aspect-ratio consistency between declared physical size and pixel dimensions
- Colour space matches `colour_space`
- Asset present, non-corrupt, checksum recorded

### 15.2 Alpha quality — new

Presence of an alpha channel is necessary but not sufficient.

- A real alpha channel exists
- No accidental opaque background plane
- **Partial-alpha budget:** pixels with alpha strictly between opaque and transparent are confined to a
  narrow edge band. Large soft regions — glows, drop shadows, gradients fading to transparent — are
  reported, because over a DTF white underbase they print as visible haze or film residue.
- No fully transparent pixels carrying stray colour data

**Rationale:** this is the failure mode that looks premium on screen and ruins a physical transfer. It is
invisible until a sample exists, which is precisely why it must be caught deterministically.

### 15.3 Minimum feature size — new

- Minimum stroke/detail width, measured at final print scale, ≥ `min_reliable_stroke_mm`
- Rendered text below the printer's reliable threshold is reported

Thresholds are populated from measured Gate 1 calibration results (§17), not from assumption.

### 15.4 Rendered bounds — new

- Actual inked pixel bounding box compared against declared physical dimensions
- Unexpected transparent margin, or artwork exceeding the declared print area, is reported

Catches silent rescaling and mis-declared sizes before they reach film.

---

## 16. Printer Package

Deterministic, human-readable, and unambiguous about which file is production artwork.

```
MIND-HACKER-007/
├── PRINT/
│   └── mind-hacker-007.png        ← production artwork; the only printable file
├── PREVIEW/
│   ├── black-back.jpg             ← approval only; NOT for printing
│   └── black-front.jpg
├── print-spec.txt
└── manifest.json                  ← checksums, provenance, validation result
```

The print spec records: design ID and name; garment, colour, size; placement; **exact physical width and
height in mm**; process and profile; quantity; explicit **"DO NOT RESIZE"** where applicable; printer
notes; and the validation summary.

Preview and production assets must be unmistakably separated by directory and naming. `manifest.json`
carries checksums for every asset and the provenance record from §9.

---

## 17. Mockups

V1 mockups are **visual approval tools**, not simulations.

Required: front and back; garment colour; artwork placement and scale; approximate true-to-life size
representation. Flat 2D compositing onto garment photography. Physically simulated fabric deformation is
explicitly out of scope.

Mockups are always tagged as preview assets and can never be mistaken for production artwork.

---

## 18. Licensing Register

Verified at Gate 0 by fetching each project's actual `LICENSE` file.

| Component | Licence | V1 status |
|---|---|---|
| Pillow | HPND | Permitted |
| Python stdlib / numpy | PSF / BSD | Permitted |
| VTracer | MIT | Clean, **not used in V1** (§13) |
| Fabric.js | MIT | Clean, deferred to Gate 2 UI |
| BiRefNet | MIT | Approved alpha fallback |
| InSPyReNet / transparent-background | MIT | Approved alpha fallback |
| Qwen-Image (code + weights) | Apache-2.0 | Documented future option only (§8.5) |
| rembg | MIT (**code only**) | Permitted only after auditing the specific weights |
| ComfyUI | GPL-3.0 | **Excluded** |
| ComfyUI-RMBG | GPL-3.0 | **Excluded** |
| **BRIA RMBG-2.0** | **CC BY-NC 4.0** | **PROHIBITED — commercial use requires a paid BRIA agreement** |

### 18.1 Standing rules

1. Public visibility on GitHub does not imply a right to use.
2. **Code licence and model-weights licence are separate.** Verify both.
3. For hosted providers, verify the **terms governing commercial use of generated outputs**. This is
   distinct from weights licensing and becomes the dominant question when using an API.
4. Licence findings are recorded in this register before a dependency is adopted.

---

## 19. Storage and Durability

### 19.1 Separation

Structured metadata and binary assets are stored separately. Assets sit behind an `AssetStore` interface
so the backing store can change without touching the core.

### 19.2 V1 form

File-backed manifest (JSON or SQLite) plus a filesystem asset tree. No database server.

### 19.3 Durability — mandatory

**The current engineering environment is ephemeral and retains nothing.** Therefore:

> **No Gate is complete until its evidence exists outside the engineering environment.**

Acceptable durable destinations: committed and pushed to the repository; delivered to the operator;
exported to connected durable storage. Every asset carries a stable identifier; exported assets carry
checksums.

---

## 20. Security

Secrets outside source control, always. No API keys in Git. A committed `.env.example` carries names and
never values. Validate uploaded file types; sanitise filenames; prevent path traversal; size-limit
uploads. When hosted models are used, the operator must be able to determine which assets leave the local
system. Log processing failures without leaking secrets.

---

## 21. Testing

**Unit — exhaustive, on pure logic:** unit conversion, effective-DPI computation, required-pixel
derivation, printer-limit checks, all validation rules, alpha-quality thresholds, minimum-feature
computation, bounds checking, manifest generation.

**Golden-file:** known input assets producing known transparency, dimensions, package structure and
manifest contents.

**Integration:** provider adapters (including `FileProvider`), asset persistence, package export, failure
recovery.

**Manual visual QA:** generated design quality, alpha edges, mockups, typography, and — decisively —
physical prints. AI visual quality cannot be fully reduced to unit tests. Physical print quality cannot be
tested in software at all.

---

## 22. Failure Handling

Errors must be understandable and non-destructive. Generation failure must never destroy a previously
approved revision. Transparency failure falls back to an alternative method rather than terminating the
workflow. Provider unavailability must degrade to `FileProvider` rather than halting the pipeline.
Validation FAIL blocks export but preserves all work.

---

## 23. Gates

| Gate | Content | Exit |
|---|---|---|
| **0 — Audit** | Read-only architecture and environment audit | ✅ **Complete.** PASS WITH CHANGES, accepted |
| **1 — Physical proof** | Smallest experiment proving idea → transfer → pressed shirt | ≥1 acceptable physical shirt, reproduced; measured calibration data; evidence-based printer profile |
| **2 — Core application** | Design/revision model, provenance, refinement, asset store, library basics | Full design workflow through the application |
| **3 — Print production** | Printer profiles, mockups, packages, full validation surface | Validated printer package with no manual technical preparation |
| **4 — Collections & UX** | Collection briefs, coherent multi-design generation, improved library, optional browser UI | Efficient multi-design collection production |

Gate 1 is specified in `GATE_1_PHYSICAL_PIPELINE_PLAN.md`. **Do not proceed deep into UI work before the
physical pipeline is proven.**

---

## 24. Hard Architectural Rules

1. The print-processing core is UI-agnostic. Adding a browser UI later must require **zero** core changes.
2. **AI-rendered wording never enters a production print asset.**
3. Physical dimensions and effective DPI are computed deterministically, never inferred from metadata.
4. No artwork is print-ready without passing validation against a **real** printer profile.
5. One printer's requirements are never hard-coded into global logic.
6. Image and LLM providers remain replaceable. No provider name appears in `core/`.
7. `FileProvider` remains a working non-AI path.
8. Revisions are preserved non-destructively; approved artwork is never destructively overwritten.
9. Preview assets and production assets are unmistakably separated.
10. No dependency is adopted before its licence — code *and* weights — is verified and registered.
11. No component is added that does not measurably improve idea → pressed shirt.
12. No local GPU dependency in V1.
13. Not every design becomes a vector.
14. Evidence must reach durable storage before a gate is declared complete.
15. **Physical print quality is the ultimate acceptance criterion.**

---

## 25. Definition of Done — V1

- Operator creates a design conversationally, with multiple creative directions available
- Revisions preserved with provenance
- Exact typography deterministic and correct
- Transparent artwork produced, passing alpha-quality validation
- Physical size defined; effective DPI computed and validated
- Alpha-quality, minimum-feature and rendered-bounds checks operational
- Garment mockup available for approval
- Printer profile stored, sourced from a real printer
- Printer package generated and passing deterministic validation
- **The workflow has produced successful real-world heat-pressed T-shirts**
- Core workflows carry automated tests
- Setup and operation documented
- No secrets in source control
- Dependency and model licensing reviewed and recorded

---

## 26. Open Questions

Resolved at Gate 0: development hardware; local-vs-cloud inference; GPU requirement; deployment target for
V1; the browser-UI question.

Outstanding:

| # | Question | Blocks |
|---|---|---|
| 1 | Printer requirements — see `PRINTER_REQUIREMENTS_CHECKLIST.md` | **Gate 1 physical production** |
| 2 | Hosted image-provider credential availability | Gate 1 AI generation (not the pipeline — `FileProvider` covers it) |
| 3 | Whether egress policy can be widened to a second provider | Provider redundancy |
| 4 | Confirmed transfer process — DTF or otherwise | Whether §13 is deleted or reinstated |
| 5 | Garment sizes carried, and whether print dimensions vary by size | Physical sizing model |
| 6 | Commercial-use terms for generated outputs of the chosen hosted provider | Commercial sale of output |

---

## 27. Final Principle

The system exists to make excellent physical T-shirts, not impressive AI demos. Every decision is judged
against one question:

> **Does this make it faster and more reliable to go from an idea in the operator's head to a professional
> transfer that can be heat-pressed onto a real T-shirt?**

If a feature, model, dependency or infrastructure component does not materially improve that outcome, it
is not part of V1.
