# Printer Requirements Checklist

**Document:** `PRINTER_REQUIREMENTS_CHECKLIST.md`
**Version:** 1.0
**Status:** **BLOCKING for Gate 1 physical production.**
**Date:** 2026-08-16 (partial evidence recorded at Gate 0.5)

The answers below populate the printer profile. No transfer is ordered against assumptions, and no
artwork is declared print-ready without a profile sourced from these replies.

> ### Partial evidence received — 2 of 14
>
> The printer has stated **"PNG without background"** (2026-08-16). That confirms **exactly two** things:
> **Q2** — PNG accepted/preferred — and **Q6** — transparency required.
>
> **Nothing else is inferred from it.** Not DPI, colour profile, mirroring, maximum dimensions, minimum
> feature size, or transfer technology.
>
> Both questions are **retained in Part A**: the reply was informal, and confirmation costs nothing.
>
> **This checklist remains blocking.** The two answered items are among the *least* consequential in the
> profile. Every field that gates validation — minimum detail (**Q9**), underbase behaviour (**Q7**), DPI
> (**Q3**) and maximum dimensions (**Q4**) — is still open.
>
> Supplied T-shirt examples show desired finished merchandise. They are **not** evidence of the printer's
> technical process.

**Part A** is written to be sent to the printer as-is. **Part B** is internal and should not be sent.

---

# PART A — Send this to the printer

> Copy from here to the end of Part A.

---

Hello,

We're setting up an automated artwork-preparation process and want to make sure every file we send you is
correct first time, with no rework at your end. Could you answer the questions below? Short answers are
perfect — and if any question doesn't apply to how you work, just say so.

**1. Process.** What print/transfer process will you be using for our work — DTF, DTG, screen print,
sublimation, vinyl, or something else?

**2. File formats.** Which file formats do you accept, and which do you *prefer*?

**3. Resolution.** What DPI do you require or prefer? Should that be measured at the final printed size?

**4. Maximum dimensions.** What is the maximum printable width and height of a single transfer, in mm?

**5. Colour mode.** Do you want files in **RGB** or **CMYK**? If RGB, does your RIP handle the conversion?
Do you use a specific colour profile we should supply or match?

**6. Transparency.** Do you require a transparent background? Is a flattened file with a white background
ever acceptable, or would it print as a visible box?

**7. White underbase.** How do you handle the white underbase — is it generated automatically by your RIP,
or do we need to supply it? And how do **semi-transparent pixels** behave — soft shadows, glows, or edges
that fade out? Do these print cleanly, or should we avoid them entirely?

**8. Mirroring.** Does your RIP mirror the artwork automatically, or do you need us to supply it
pre-mirrored?

**9. Minimum detail.** What is the smallest line width and smallest text size you can reliably reproduce?
A figure in mm or pt is ideal. Below what size would you expect detail to break up or fail to transfer?

**10. Resizing.** If a file arrives at the wrong dimensions, do you resize it, or reject it and come back
to us? We'd prefer you never resize — we want to supply artwork at exact final size.

**11. Cutting.** Do you cut/contour the transfers, or do they arrive as sheets for us to cut ourselves?

**12. Cost.** What does a single transfer cost at the sizes we're likely to order? Is there a minimum
order or setup fee, and does cost change with sheet size or quantity?

**13. Turnaround.** What is your typical turnaround from receiving a file to us receiving transfers?

**14. Anything else.** Is there anything else about how you like files supplied — naming, layout, gang
sheets, spacing between designs, bleed, safe margins, file delivery method — that would save you time or
avoid problems? Anything that commonly goes wrong with files you receive is especially useful to know.

Thanks very much.

---

> End of Part A.

---

# PART B — Internal notes (do not send)

## B.1 Capture table

Record answers verbatim. Leave unanswered fields **blank** — never fill them with an assumption.

| # | Question | Profile field | Answer | Date |
|---|---|---|---|---|
| 1 | Process | `process` | | |
| 2 | Accepted formats | `accepted_formats` | PNG *(partial — "PNG without background")* | 2026-08-16 |
| 2 | Preferred format | `preferred_format` | PNG *(partial)* | 2026-08-16 |
| 3 | DPI | `required_dpi` | | |
| 4 | Max width (mm) | `max_width_mm` | | |
| 4 | Max height (mm) | `max_height_mm` | | |
| 5 | Colour mode | `colour_space` | | |
| 6 | Transparency required | `requires_transparency` | true *(partial — "without background")* | 2026-08-16 |
| 7 | White underbase / partial alpha | `white_underbase_behaviour` | | |
| 8 | RIP mirrors | `rip_handles_mirroring` | | |
| 9 | Min reliable stroke/text | `min_reliable_stroke_mm` | | |
| 10 | Printer resizes files | `printer_resizes_files` | | |
| 11 | Cutting responsibility | `cutting_responsibility` | | |
| 12 | Cost per transfer | `cost_per_transfer` | | |
| 13 | Turnaround | `turnaround` | | |
| 14 | Other requirements | `special_instructions` / `custom_requirements` | | |

## B.2 Why each answer matters

Each of these changes something concrete in the pipeline. Ordered by consequence.

| # | What it determines |
|---|---|
| **9** | **Populates the minimum-feature validator (spec §15.3).** Without it that check cannot run, and thin detail failures are only discovered on physical film. The single most valuable number on this list, and the one printers are least often asked for. |
| **7** | **Populates the alpha-quality validator (spec §15.2).** Determines whether soft edges, glows and gradients-to-transparent are usable at all. This is the failure mode that looks premium on screen and prints as haze. |
| **8** | Mirroring is binary and unforgiving. Industry convention is that the RIP mirrors and files must **not** be pre-mirrored — a pre-mirrored file presses backwards. Convention is not confirmation; a wrong assumption costs a transfer. |
| **5** | RGB vs CMYK. Convention is RGB, because the RIP converts and produces better colour from an RGB source than from an operator-converted file. Getting this wrong degrades every print subtly rather than obviously. |
| **3 + 4** | Feed the deterministic sizing engine (spec §12). Required pixel dimensions are derived as `ceil((mm / 25.4) × dpi)`; max dimensions bound every design. |
| **1** | Confirms whether the raster-only decision holds. A vector-consuming process reopens **D-09**. |
| **2** | Confirms PNG is accepted and preferred. If a vector format is *preferred*, that is the reinstatement trigger for vectorization. |
| **6** | Confirms transparency handling and whether a flattened file would print as a visible box. |
| **10** | If the printer silently resizes, our exact-size guarantee is void and the rendered-bounds check (spec §15.4) becomes the last line of defence. We want an explicit "we never resize". |
| **11** | Determines whether cut margins and spacing must be built into exports. |
| **12 + 13** | Bound Gate 1 iteration economics: how many physical attempts are affordable, and how long each costs in elapsed days. |
| **14** | Open-ended by design. Printers routinely have workflow preferences nobody thinks to ask about, and "what usually goes wrong" is often the highest-value answer on the page. |

## B.3 Handling the replies

1. Record answers verbatim in B.1 before interpreting them.
2. Populate the printer profile (spec §14). Unanswered → `null`. **`null` is never a default.**
3. If the process is **not** DTF, or a vector format is accepted/preferred, flag **D-09** for review before
   Gate 1 proceeds.
4. If minimum detail (9) or underbase behaviour (7) is not answered, the Gate 1 calibration sheet is the
   fallback: it measures both empirically. Ask again anyway — a stated figure and a measured figure
   together are far stronger than either alone, and a mismatch is itself useful information.
5. Commit the completed profile to the repository. It is Gate 1 evidence and must survive the environment
   (**D-13**).

## B.4 Gate 1 dependency

Gate 1 Stage 0 is complete when Part A is answered and the profile is populated and committed. **Physical
production does not begin before that.** Software stages of Gate 1 may proceed in parallel, but no
transfer is ordered.
