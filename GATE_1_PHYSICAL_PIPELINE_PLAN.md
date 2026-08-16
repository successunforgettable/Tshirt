# Gate 1 — Physical Pipeline Proof Plan

**Document:** `GATE_1_PHYSICAL_PIPELINE_PLAN.md`
**Version:** 1.1 — subject updated at Gate 0.5
**Status:** Approved plan. **Not yet executed.**
**Date:** 2026-08-16
**Depends on:** `AI_TSHIRT_STUDIO_TECHNICAL_SPEC_V1.md` (v1.2), `AI_TSHIRT_STUDIO_ARCHITECTURE_DECISION_V1.md` (v1.1), `PRINTER_REQUIREMENTS_CHECKLIST.md`, `brand/the-incredible-you.json`

> **Gate 0.5 changes:** the test *subject* changed from a generic concept to real brand work; the calibration
> sheet gained brand red and IP string-fidelity probes; validation gained the canonical-string assertion.
> **Structure, stage count and scope are unchanged** — Gate 1 remains a single fixed physical-pipeline proof.

---

## 1. Purpose

Prove the **physical** chain end to end, with measurement rather than impression:

```
idea / supplied image
   → deterministic typography
   → transparency
   → exact physical sizing
   → validation
   → printer file
   → transfer
   → heat press
   → measured physical result
```

Gate 1 exists to find out what the printer, the ink and the press actually do — not to build software.
Software is written only where it is the shortest path to a measurable physical result.

### 1.1 Non-goals

Gate 1 does **not** build: a database, a web UI, a job queue, revision-tree navigation, a Creative Director
service, multiple creative directions, collections, mockups, vectorization, ComfyUI, or upscaling unless
Stage 5 proves it necessary.

Gate 1 does **not** attempt to produce a commercially perfect shirt. It attempts to produce a shirt whose
deviations from the digital file are **understood and attributable**.

### 1.2 Governing principle

> A visually attractive screen image is not evidence. A pressed shirt with a ruler next to it is.

---

## 2. Exit Criteria

Gate 1 is complete when **all** hold:

1. ≥1 heat-pressed T-shirt judged physically acceptable.
2. The result is **reproduced** on a second press — a single good shirt can be luck.
3. A printer profile exists, populated from the printer's own answers **and** from measured calibration
   data.
4. Measured values for **minimum reliable stroke width** and **partial-alpha behaviour** are recorded and
   encoded as validator thresholds (spec §15.2, §15.3).
5. **Proprietary terminology survived the transfer with exact spelling** — hyphens and capitalisation
   intact — with the smallest reliable size recorded per term (spec §15.5, **D-06**).
6. Every deviation between the digital file and the physical shirt is either explained or explicitly
   logged as unexplained.
7. All evidence exists **outside** the engineering environment (**D-13**).

Failing to produce an acceptable shirt is **not** a failed gate, provided the cause is identified. An
unexplained failure is a failed gate.

---

## 3. Stages

### Stage 0 — Printer profile *(BLOCKING — no code)*

Send Part A of `PRINTER_REQUIREMENTS_CHECKLIST.md`. Record answers. Populate and commit the profile.

**Physical production does not begin until this is complete.** Software stages may run in parallel; no
transfer is ordered.

**Output:** committed `printer_profile.json`.

---

### Stage 1 — One fixed concept

A single hardcoded concept. No Creative Director, no LLM abstraction, no multiple directions.

**Subject: `THE INCREDIBLE YOU`** — black tee, large back graphic, white artwork with a brand-red accent.
`usage_tier: brand_inspired`.

**Why this one.** It is typography-led, which stresses the highest-risk rule in the specification
(**D-06**); it uses a limited palette, which tests deterministic keying (**D-08**); and it has a single
accent colour, which gives the colour comparison in Stage 10 something specific to converge on. Using real
brand work rather than a throwaway concept costs nothing and produces a genuinely usable first shirt.

**Why the brand name and not a proprietary term.** `THE INCREDIBLE YOU` has known, unambiguous spelling and
requires no meaning to design around. Using `N-Codes` or `Inner DNA` as the *headline* would force exactly
the invented-meaning decision **D-16** prohibits — designing around a term whose meaning has not been
supplied. Those terms are instead tested for string fidelity in the Stage 7 text ladder, where they need no
interpretation at all.

**Why this is not official logo usage.** The words are typeset as an **original typographic merchandise
composition** via deterministic typography. The official brand mark is a separate supplied asset, is not
available, and must not be reconstructed, traced or approximated from screenshots (**D-17**). Gate 1 uses
`usage_tier: brand_inspired`, never `official_logo`.

**Output:** a committed brief JSON conforming to spec §6.2, with `message_is_authoritative: true` and a
`brand` block carrying `authoritative_strings: ["THE INCREDIBLE YOU"]`.

---

### Stage 2 — Artwork acquisition

Two paths, both exercised.

**2a — Hosted provider.** One direct call to the reachable hosted provider. No abstraction layer yet, no
provider survey. Generate the **graphic only**; any model-rendered text is disposable placeholder
(**D-06**).

Generate onto a **flat, uniform, high-contrast background** to enable deterministic keying at Stage 4.

**2b — `FileProvider`.** Run the identical downstream pipeline against a hand-supplied image.

**Why 2b is not optional.** It proves the deterministic print chain independently of AI availability,
credentials and egress policy. If Stage 2a is blocked — no key, changed policy, provider outage — **Gate 1
still proceeds on 2b**. This is the decision that stops a network constraint from blocking a physical
experiment.

**Output:** raw artwork asset(s) with provenance recorded (spec §9).

---

### Stage 3 — Deterministic typography

Composite final wording from a **pinned font file**, driven by a declarative layout object (text, font,
size, tracking, alignment, position, colour).

No UI. The operator iterates the layout conversationally; the core renders it. This is the same function a
later browser editor will call (**D-07**).

Any placeholder text from Stage 2 must be verifiably removed or covered. **Confirm by inspection before
proceeding** — this is the check that makes **D-06** real rather than aspirational.

**Output:** composited artwork with correct, deterministic wording.

---

### Stage 4 — Transparency

Deterministic keying first (**D-08**): threshold the flat background, refine edges.

Fall back to a permissively licensed segmentation model (BiRefNet or InSPyReNet, both MIT) **only if**
keying proves inadequate.

**Record which method was needed.** If deterministic keying suffices for this artwork style, the
segmentation fallback may never need building — a real V1 saving. If it does not suffice, that is an early
and cheap finding.

**Output:** transparent PNG. Method and parameters recorded.

---

### Stage 5 — Exact physical sizing

Compute, never guess:

```
required_px = ceil((physical_mm / 25.4) × required_dpi)
```

Worked example: 280 mm wide back print at 300 DPI → **3307 px**.

Assert the rendered file against the computation. If artwork falls short of the requirement, note it —
upscaling enters scope **only** if this stage proves it necessary.

**Output:** print asset at exact required pixel dimensions, with declared physical dimensions attached.

---

### Stage 6 — Validation

Run the deterministic validator against the Stage 0 profile. Must return **PASS** before anything is sent.

Includes the four additions from **D-10**:

- **Alpha quality** — partial-alpha confined to a narrow edge band; no stray colour in transparent pixels;
  no accidental opaque plane.
- **Minimum feature size** — measured at final print scale against `min_reliable_stroke_mm`.
- **Rendered bounds** — actual inked extents versus declared physical size.
- **Canonical-string assertion** — composited authoritative text byte-matches its source (spec §15.5).
  For Gate 1 that is `THE INCREDIBLE YOU`. Any mismatch is a FAIL, never a WARNING.

Plus format, pixel dimensions, effective DPI, colour space, maximum dimensions, aspect consistency, and
checksum.

**Output:** validation report, committed. A FAIL blocks the send.

---

### Stage 7 — Calibration sheet *(highest-value item in Gate 1)*

Placed on the **same transfer sheet** as the design, in unused sheet area.

#### Why this exists

Without a control, a disappointing shirt tells you nothing about **where** the fault lies — the model, the
file preparation, the RIP, the ink, or the press. With a control, the same physical sample yields
measurable data about the printer itself.

It converts "this looks a bit off" into numbers, and it turns the printer profile from a set of stated
claims into measured fact. It costs one extra area on a transfer already being paid for.

#### Contents

| Element | Specification | Answers |
|---|---|---|
| **Colour ramp** | Patches at known RGB values, **including brand red** (hex required — spec §26 Q7), each labelled with its hex value | How far does printed colour drift from digital? **Is brand red reproducible?** This is the colour that will be reprinted indefinitely |
| **Greyscale wedge** | 0%, 10%, 25%, 50%, 75%, 90%, 100% | Tonal response and where highlights/shadows collapse |
| **Stroke ladder** | Solid lines at 0.25, 0.5, 1, 2, 3, 4 mm at final print scale, labelled | **Measured minimum reliable stroke** → validator threshold (spec §15.3) |
| **Text ladder** | Strings at 6, 8, 10, 12, 16 pt at final scale. **Include `N-Codes`, `E-Codes` and `Inner DNA` verbatim** | Smallest legible text after transfer, **and hyphen/mixed-case fidelity on real proprietary terminology at every size** |
| **Edge pair** | One hard-edged shape beside one with a soft gradient fading to transparent | **Partial-alpha behaviour over white underbase** → validator threshold (spec §15.2). Directly tests the haze failure mode |
| **Reference ruler** | Printed 100 mm scale with 10 mm graduations | Detects RIP rescaling. Measured with a physical ruler at Stage 10 |
| **Registration marks** | Corner marks at known separation | Distortion and dimensional accuracy across the sheet |
| **Orientation marker** | Asymmetric glyph, e.g. a large "R" | Confirms mirroring behaviour unambiguously |

#### Rules

- Every element **labelled in print** with its nominal value. An unlabelled calibration mark is unreadable
  after transfer.
- **Proprietary terms in the text ladder are string-fidelity probes only.** They are typeset verbatim via
  deterministic typography and carry no illustration, symbol or visual interpretation. This measures
  hyphen and capitalisation survival at print scale — the characters most likely to degrade — while
  requiring **no design decision about meaning** (**D-16**).
- Generated by the **same pipeline** as the artwork — same sizing, keying and export path. A calibration
  sheet produced by a different route measures the wrong thing.
- Committed as a versioned asset and reused for every future printer or process change.

**Output:** calibration sheet asset, committed, positioned on the transfer sheet.

---

### Stage 8 — Durable export *(before sending)*

Assemble the printer package (spec §16) and push everything to the repository: brief, artwork, print
asset, calibration sheet, validation report, printer profile, provenance manifest with checksums.

**Nothing may exist only inside the engineering environment (D-13).** The container is reclaimed on
inactivity and retains nothing. Deliver the print file to the operator by a durable route, since it must
reach the printer from outside the sandbox.

**Output:** committed, pushed package. Print file in the operator's hands.

---

### Stage 9 — Physical production

1. Send the package to the printer exactly as specified — **do not** pre-mirror unless Stage 0 says to.
2. Receive the transfer. **Inspect the film before pressing**: check edge quality, colour, detail
   integrity, and calibration-sheet fidelity. Faults visible on film are printer/file faults; faults
   appearing only after pressing are press/material faults. Recording this distinction here is what makes
   Stage 10 diagnostic rather than speculative.
3. Heat-press onto the **actual target garment** — correct colour, style and size.
4. **Press a second identical shirt.** Repeatability is part of the proof.
5. Record press parameters: temperature, time, pressure, peel (hot/cold), and any second press.

**Output:** two pressed shirts; the pressed calibration sheet; recorded press settings.

---

### Stage 10 — Measurement

Measurement, not impression.

| Check | Method |
|---|---|
| **Dimensional accuracy** | Physically measure the printed 100 mm ruler. Any deviation means rescaling occurred somewhere. Measure the design's actual width against the declared value. |
| **Minimum stroke** | Identify the finest stroke that survived intact. **Record as the validator threshold.** |
| **Text legibility** | Identify the smallest text size that survived. |
| **Partial alpha** | Compare hard-edge and soft-edge shapes. Is haze, residue or a visible film boundary present? **Record as the alpha-quality threshold.** |
| **Colour** | Photograph the colour ramp beside the digital file under controlled, consistent lighting. Note the drift on the accent colour specifically. |
| **Typography** | Verify wording is exactly correct — the direct test of **D-06**. |
| **IP string fidelity** | Inspect `N-Codes`, `E-Codes`, `Inner DNA` in the text ladder at every size. **Confirm hyphens survived and capitalisation is exact.** Record the smallest size at which each remains correct — this is the physical counterpart to the §15.5 assertion. |
| **Orientation** | Confirm the orientation marker reads correctly, settling the mirroring question empirically. |
| **Placement & size** | Measure position on the garment against intent. |
| **Durability** *(optional but recommended)* | Wash once and re-inspect. Cracking, lifting or fade appears here, not at press time. |

Photograph everything under consistent lighting, alongside the digital file where comparison is the point.

**Output:** measurement record with photographs, committed. Validator thresholds updated. Printer profile
updated with measured values alongside the printer's stated values — **retain both**; a mismatch between
stated and measured is itself a finding worth keeping.

---

## 4. Deliverables

| Deliverable | Destination |
|---|---|
| Populated printer profile (stated + measured) | Repository |
| Brief JSON, artwork assets, final print asset | Repository |
| Calibration sheet (versioned, reusable) | Repository |
| Validation report | Repository |
| Provenance manifest with checksums | Repository |
| Measurement record + photographs | Repository |
| Validator thresholds derived from measurement | Repository, as code constants |
| Two pressed shirts + pressed calibration sheet | Physical, photographed |

---

## 5. Scope of Code Written

Only what Stages 2–8 require:

```
providers/       hosted provider call + FileProvider
core/compose/    typography compositing from declarative layout
core/alpha/      deterministic keying
core/size/       mm ⇄ px ⇄ effective DPI            (pure, fully tested)
core/validate/   validation incl. D-10 additions     (pure, fully tested)
core/package/    export tree + manifest + checksums
cli/             thin adapter
```

**Estimated: 800–1,500 lines**, of which the pure logic in `size/` and `validate/` carries most of the
correctness burden and should approach full unit coverage.

Written under **D-01**: the core takes values and returns values, with no knowledge of its caller. A
browser UI added later must require zero core changes.

**Not written:** database, web server, queue, revision navigation, Creative Director service, mockups,
vectorization, upscaling (unless Stage 5 forces it).

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| Printer answers delayed | Stages 1–8 proceed in parallel; only production blocks |
| Hosted provider unavailable or uncredentialed | **Stage 2b (`FileProvider`) carries the gate.** The physical proof does not depend on AI access |
| Deterministic keying inadequate | Licence-cleared MIT fallback already selected (**D-08**) |
| Artwork below required resolution | Detected deterministically at Stage 5; upscaling scoped only if forced |
| Transfer arrives faulty | Film inspected before pressing (Stage 9.2), separating printer faults from press faults |
| Press settings wrong | Recorded per attempt; calibration sheet isolates press effects from file effects |
| Result disappointing but cause unclear | **This is what the calibration sheet exists to prevent** |
| Evidence lost with the container | Stage 8 pushes before sending (**D-13**) |
| Scope creep into application building | Non-goals in §1.1 are explicit; §5 bounds the code |

---

## 7. Timeline Shape

Elapsed time is dominated by the printer, not by engineering.

| Phase | Driver |
|---|---|
| Stage 0 | Printer response time — **start immediately** |
| Stages 1–8 | Engineering; runs parallel to Stage 0 |
| Stage 9 | Printer turnaround + shipping (the long pole) |
| Stage 10 | Hours once the shirts exist |

Stage 0 is the critical path and costs one email. It should be sent before any code is written.

---

## 8. After Gate 1

Gate 1 findings feed Gate 2 directly: measured validator thresholds become code constants; the printer
profile becomes the first real profile; the keying result determines whether segmentation is ever built;
and the calibration sheet becomes the standing instrument for any new printer, process or material.

**Do not begin Gate 2 until Gate 1 exit criteria are met and evidence is committed.**

---

## 9. Execution Status

**NOT STARTED.** This document is a plan. No Gate 1 stage has been executed, no code written, no packages
installed, no provider integrated, no transfer ordered.
