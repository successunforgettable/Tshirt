# Gate 1a — Physical Inspection & Measurement Record

**Status:** To be completed AFTER the transfer is printed and heat-pressed.
**Purpose:** Turn the calibration transfer into measured printer tolerances.

Until this document is filled in, Gate 1a is **SOFTWARE READY — AWAITING PHYSICAL
VALIDATION**, not PASS.

You need: a steel ruler with millimetre graduations, good consistent light (daylight or
one neutral lamp — not mixed), a phone camera, and a magnifier or phone-zoom for the fine
detail.

---

## Before pressing — inspect the transfer film

Do this first. It is the only chance to separate **printer/file faults** from
**press/material faults**, and once pressed the distinction is lost.

| # | Check | Record |
|---|---|---|
| 0.1 | Does the film look correct, complete and unmirrored? | |
| 0.2 | Is the calibration sheet present at full size alongside the design? | |
| 0.3 | Any banding, streaking, or missing white underbase visible on the film? | |
| 0.4 | Do the finest stroke-ladder lines exist on the film at all? | |

---

## Press

Record the settings actually used — without these, a good result cannot be repeated.

| Setting | Value |
|---|---|
| Temperature | |
| Time | |
| Pressure | |
| Peel (hot / warm / cold) | |
| Second press applied? | |
| Garment (colour, style, size) | black T-shirt, size M |

**Press two identical shirts.** A single good shirt can be luck; repeatability is part of
the proof.

### Placement on a size M

The artwork is **280.1 mm wide × 270.0 mm high**. Suggested starting placement:

- **Horizontally:** centred on the body, measured between the side seams — not by eye.
- **Vertically:** top edge of the upper rule about **70 mm below the collar seam**. The
  design then finishes roughly 340 mm below the collar, around mid-torso on an M.

Two things worth knowing before you press, neither of which changes the file:

1. **280 mm is at the upper end of the printable width for a size M.** That is deliberate
   — it is a large centre-front print — but it will sit close to edge-to-edge across the
   chest. If it turns out wider than you want on the body, the fix is a smaller target
   width in the next build, not a resize of this file.
2. **Measure and mark before pressing.** Once bonded, placement cannot be corrected, and
   placement error is easy to mistake for a file error when reviewing the result.

Record what you actually used: distance below collar ______ mm, centred by ______
(seam measurement / eye).

---

## 1. Dimensional accuracy — do this first

Everything else depends on the file not having been rescaled.

1. Measure the printed **100 mm ruler** on the calibration sheet with a steel rule.
   - Measured length: ______ mm
   - **If this is not 100 mm ± 1 mm, the RIP rescaled the file.** Stop and report it —
     every other measurement below is then suspect.
2. Measure the **design width** across the widest point of `INCREDIBLE`.
   - Expected **280.1 mm**. Measured: ______ mm
3. Measure the **design height** (top of the upper rule to the bottom of the lower rule).
   - Expected **270.0 mm**. Measured: ______ mm
4. Measure between opposing **registration marks** on the calibration sheet to check for
   distortion across the sheet.

→ Answers the profile field `printer_resizes_files`.

---

## 2. Minimum reliable stroke — the most valuable number

On the **stroke ladder** (section 5), find the thinnest line that transferred **solid,
continuous and unbroken**.

| Line | Survived intact? | Notes |
|---|---|---|
| 0.25 mm | | |
| 0.5 mm | | |
| 1.0 mm | | |
| 2.0 mm | | |
| 3.0 mm | | |
| 4.0 mm | | |

**Thinnest fully reliable stroke: ______ mm**

→ Becomes `min_reliable_stroke_mm`. This turns the validator's `minimum_feature` check
from PENDING into a real PASS/FAIL.

---

## 3. Partial alpha / underbase haze — the dominant DTF failure mode

**3a. Alpha step wedge** (section 3). Each patch is white at a known alpha.

| Patch | Clean? | Hazy / greyish? | Visible film edge? |
|---|---|---|---|
| a10% | | | |
| a25% | | | |
| a50% | | | |
| a75% | | | |
| a90% | | | |
| a100% | | | |

**Lowest alpha that still prints acceptably: ______ %**

**3b. Hard edge vs fade** (section 7). Compare the two blocks.

- Hard-edged block: clean edge? ______
- Faded block: where does it stop looking intentional and start looking like dirt or
  residue? ______
- Is there a visible carrier-film boundary around the fade after washing? ______

→ Becomes `max_partial_alpha_ratio` and `white_underbase_behaviour`. If the fade prints
badly, **no production design may use gradients to transparent** — a rule worth knowing
before designing, not after.

---

## 4. Negative space / counters

On the **negative space test** (section 6), find the smallest gap that stayed open rather
than filling in with ink.

| Gap | Stayed open? |
|---|---|
| 0.25 mm | |
| 0.5 mm | |
| 1.0 mm | |
| 1.5 mm | |
| 2.0 mm | |
| 3.0 mm | |

**Smallest reliable gap: ______ mm**

→ Becomes `min_negative_space_mm`. Governs how tight letter counters and internal detail
may be.

---

## 5. Colour

**5a. Red family sweep** (section 1). Photograph the printed patches next to the on-screen
file under consistent light.

| Patch | Prints close to screen? | Drift (lighter/darker/more orange/more pink) |
|---|---|---|
| #FF0000 | | |
| #E30613 | | |
| #D0021B | | |
| #C8102E | | |
| #B71C1C | | |
| #A6192E | | |

**Which printed red looks most like the brand red you have in mind? ______**

> This does **not** define brand red. The authoritative hex must still come from your
> real brand assets. It tells you how this printer treats reds as a family, so that when
> the real value arrives you can predict its behaviour instead of guessing.

**5b. Greyscale wedge** (section 2). At which end do steps stop being distinguishable?
- Light end collapses at: ______ %
- Dark end collapses at: ______ %
- Note: 0% is black ink on a black shirt — expected to be near-invisible.

**5c. White density** (section 4). Is the solid white block fully opaque, or does the
garment show through? ______

---

## 6. IP string fidelity — the D-06 test

On the **IP string ladder** (section 8), inspect closely, with magnification.

| Size | `N-Codes` hyphen intact? | `E-Codes` hyphen intact? | `Inner DNA` spacing + caps correct? | Legible? |
|---|---|---|---|---|
| 6 pt | | | | |
| 8 pt | | | | |
| 10 pt | | | | |
| 12 pt | | | | |
| 16 pt | | | | |

**Smallest size at which all three remain exactly correct: ______ pt**

Also check `THE INCREDIBLE YOU` at 12 pt for correct spacing and capitals.

→ This is the physical counterpart to the software canonical-string assertion. The
software guarantees the right string was rendered; this confirms the printer reproduced it.

---

## 7. Orientation — confirms or refutes the mirroring assumption

Find the large **`R`** marked `ORIENT` at the top right of the calibration sheet.

- Does it read as a normal **R** on the pressed shirt? **YES / NO**

**If YES:** the assumption holds — supply artwork unmirrored, the RIP mirrors.
**If NO (it reads backwards):** the assumption is **wrong**. The profile field
`rip_handles_mirroring` becomes `false`, and future files must be pre-mirrored. Tell me
and I will change the pipeline.

---

## 8. Overall design quality

| Check | Result |
|---|---|
| Edge quality of the letterforms | |
| The 2 mm rules above and below — solid and even? | |
| Any cracking, lifting or bubbling? | |
| Placement on the garment (centred? height right?) | |
| Does it look like a shirt you would actually wear? | |
| Second pressed shirt matches the first? | |

---

## 9. Durability (recommended)

Wash once per the transfer supplier's instructions, then re-inspect. Cracking, lifting and
fade appear here rather than at press time.

| Check | After 1 wash |
|---|---|
| Cracking | |
| Lifting at edges | |
| Colour fade | |
| Fine detail loss | |
| Fade block — residue now visible? | |

---

## 10. Photographs to take

1. Full shirt, front, straight on, even light
2. Design close-up
3. Calibration sheet, full, flat
4. Stroke ladder close-up
5. Alpha step wedge close-up
6. IP string ladder close-up (magnified)
7. Ruler with a steel rule laid alongside it
8. The `R` orientation marker

---

## Outcome

- [ ] Shirt is physically acceptable
- [ ] Reproduced on a second press
- [ ] All measurements above recorded
- [ ] Every deviation explained, or explicitly logged as unexplained

**An unexplained failure is a failed gate. A failure with an identified cause is not** —
it is exactly what this transfer was bought to discover.

Once complete, return this document. The measured values become validator constants and
profile fields, replacing `assumed` and `unknown` with `confirmed`, and Gate 1a moves to
**PASS**.
