# Gate 1a — Export Check

**Status:** To be completed when the transfer arrives.
**Purpose:** Confirm our software emitted a correct DTF-ready file at the intended size.

> **Gate 1a does not assess the printer.** They are experienced and trusted, and their
> process is not under test. This checks *our* export. It also has no aesthetic or
> wearable-design criterion — Gate 1b owns that.

You need: a steel ruler with millimetre graduations, and the source PNG on screen.
Five minutes.

---

## What is being printed

**`export-check-v1.png` only** — **160.0 × 135.2 mm** at 300 DPI, transparent PNG.
One copy.

## What each element is for

| Element | Confirms |
|---|---|
| Horizontal 100 mm reference | Scale on the X axis |
| Vertical 100 mm reference | Scale on the Y axis, and non-uniform distortion a single axis cannot reveal |
| Printed intended size | The artefact states its own size, so measuring needs nothing else in hand |
| Orientation marker `R` | The artwork is not unexpectedly reversed |
| Corner registration marks | Nothing was cropped; full extent survived |
| `THE INCREDIBLE YOU` / `N-Codes` | The deterministic typography path, including a hyphenated proprietary term |
| Solid block and rules | Transparency and edge integrity, by eye |

---

## The checks

### 1. Horizontal 100 mm reference

Measure between the two full-height end stops.

- Measured: **______ mm** — pass if **100 ± 1 mm**

### 2. Vertical 100 mm reference

Same, on the vertical scale down the left side.

- Measured: **______ mm** — pass if **100 ± 1 mm**

> If the two differ by more than about 1 mm from each other, something scaled the axes
> unevenly. That is worth knowing regardless of whether either is individually in range.

### 3. Overall dimensions

The artefact prints its own intended size across the top.

- Expected **160.0 × 135.2 mm**
- Measured: **______ × ______ mm**
- Registration marks present at all four corners? **Y / N** *(absence means cropping)*

### 4. Orientation

Find the `R` marked `ORIENT` at the top right.

> **On DTF film the print is normally reversed** — that is correct, because it flips onto
> the garment. So check it the way it will end up: view the film from the reverse side, or
> press onto a scrap of fabric.

- Final orientation reads correctly? **Y / N**
- If it would press **backwards**, stop and tell me — the pipeline needs changing.

### 5. Visual comparison against the source

Put the printed transfer next to `export-check-v1.png` on screen.

| Check | Result |
|---|---|
| All elements present — nothing missing | |
| Text reads exactly `THE INCREDIBLE YOU` and `N-Codes` (hyphen intact) | |
| Solid block is solid; rules are clean and unbroken | |
| Edges are sharp, not soft or ragged | |
| No corruption, banding or artefacts that are not in the file | |

### 6. Transparency

- The transparent areas of the file carry **no ink** on the transfer? **Y / N**
- No faint box, haze or film residue where the background should be? **Y / N**

---

## Pressing

**Not required.** Dimensions can be measured on the film, and orientation can be confirmed
by viewing the film from the reverse.

Press onto **scrap fabric** only if something above is ambiguous and can only be resolved
after transfer. Do not use a good garment — this is a test artefact, not a shirt.

---

## Gate 1a PASS

- [ ] Horizontal 100 mm reference measures 100 ± 1 mm
- [ ] Vertical 100 mm reference measures 100 ± 1 mm
- [ ] Overall dimensions match the manifest
- [ ] Orientation is correct for final application
- [ ] Nothing missing, cropped or corrupted
- [ ] Transparent areas printed no ink

All six → **Gate 1a PASSES**, and Gate 1b begins.

If something fails, record what and by how much. A measured failure is diagnostic; the
numbers say whether it is our export or something in transit.

---

## What Gate 1a deliberately does not ask

Minimum stroke width · alpha/underbase tolerance · colour accuracy · negative-space limits ·
repeatability · whether the design looks good.

Those are either the printer's expertise, or Gate 1b's problem. Our software measures and
reports several of them as **advisory** in `validation.json`, but none of them gates this
export — nothing is judged against a threshold nobody supplied.
