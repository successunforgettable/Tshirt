"""Turning a typed phrase into a laid-out design brief.

The operator types a description. Something has to decide how that phrase breaks
into lines and which words carry the weight, because that decision is most of
what makes merch typography work.

The rule is read straight off the reference tees: small connecting words get
their own small line, and content words get the big lines.

    "trust the process"     ->  TRUST / the / PROCESS
    "success is a state of mind" -> SUCCESS / is a / STATE / of / MIND

An operator who disagrees can force the breaks with slashes:

    "TRUST / the / PROCESS"

which skips the heuristic entirely. The heuristic only has to be good enough to
give a useful starting point, because the operator can always override it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Words that carry grammar rather than meaning. On a T-shirt these get set small
# and quiet so the content words can shout.
CONNECTORS = {
    "a", "an", "the", "is", "are", "am", "be", "was", "were", "of", "to", "in",
    "on", "at", "for", "and", "or", "but", "if", "it", "its", "as", "so", "by",
    "with", "from", "into", "than", "then", "that", "this", "will", "shall",
    "can", "do", "does", "don't", "not", "no", "your", "my", "our", "their",
}

MAX_MAJOR_CHARS = 11     # beyond this a big line gets too small to shout


@dataclass
class Line:
    text: str
    major: bool = True

    @property
    def weight(self) -> str:
        return "major" if self.major else "minor"


@dataclass
class Brief:
    """Everything a style needs in order to lay a phrase out."""

    phrase: str
    lines: list[Line] = field(default_factory=list)
    width_mm: float = 260.0
    # A brand or seminar name carried under the slogan. Every reference tee that
    # belongs to a programme signs off this way rather than putting the name in
    # the headline, which would fight the slogan for attention.
    attribution: str | None = None

    @property
    def majors(self) -> list[Line]:
        return [ln for ln in self.lines if ln.major]

    @property
    def longest_major(self) -> Line | None:
        return max(self.majors, key=lambda ln: len(ln.text), default=None)

    @property
    def text_lines(self) -> list[str]:
        return [ln.text for ln in self.lines]


SHORT_WORD = 3      # words this length or under are happy to share a line


def _split_long(words: list[str]) -> list[list[str]]:
    """Break a run of content words into lines.

    The reference merchandise gives each substantial word its own line - STAY /
    STRONG, GREAT / THINGS / TAKE / TIME - because that is what allows the violent
    scale contrast the style depends on. Packing words together produces even,
    quiet lines instead.

    Short words are the exception: they pair with a neighbour rather than
    becoming a line of their own that would be set absurdly large.
    """
    out: list[list[str]] = []
    current: list[str] = []
    for word in words:
        if not current:
            current = [word]
            continue
        pair_ok = (len(word) <= SHORT_WORD or len(current[-1]) <= SHORT_WORD)
        fits = len(" ".join(current + [word])) <= MAX_MAJOR_CHARS
        if pair_ok and fits:
            current.append(word)
        else:
            out.append(current)
            current = [word]
    if current:
        out.append(current)
    return out


def segment(phrase: str, width_mm: float = 260.0,
            attribution: str | None = None) -> Brief:
    """Break a phrase into weighted lines.

    Explicit slashes win. Otherwise connectors are separated out and long runs of
    content words are split so each big line can still be set large.
    """
    phrase = phrase.strip()

    if "/" in phrase:
        parts = [p.strip() for p in phrase.split("/") if p.strip()]
        lines = [Line(p.upper() if len(p.split()) > 1 or p.lower() not in CONNECTORS
                      else p.lower(),
                      major=p.lower() not in CONNECTORS)
                 for p in parts]
        return Brief(phrase=phrase, lines=lines, width_mm=width_mm,
                     attribution=attribution)

    words = [w for w in re.split(r"\s+", phrase) if w]
    if not words:
        return Brief(phrase=phrase, lines=[], width_mm=width_mm,
                     attribution=attribution)

    # A connector is only minor when it is not the final word - a phrase ending
    # on "YOU" or "IT" is ending on its point, not on a preposition.
    flags = [(w.lower() in CONNECTORS and i != len(words) - 1)
             for i, w in enumerate(words)]

    lines: list[Line] = []
    i = 0
    while i < len(words):
        j = i
        while j < len(words) and flags[j] == flags[i]:
            j += 1
        run, minor = words[i:j], flags[i]
        if minor:
            lines.append(Line(" ".join(run).lower(), major=False))
        else:
            for chunk in _split_long(run):
                lines.append(Line(" ".join(chunk).upper(), major=True))
        i = j

    return Brief(phrase=phrase, lines=lines, width_mm=width_mm,
                 attribution=attribution)
