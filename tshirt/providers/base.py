"""Image provider interface.

Gate 1a ships one implementation (`FileProvider`). The seam is therefore declared
but NOT yet proven — proving it needs a second implementation, and no hosted
provider is reachable or credentialed in the current environment. That limitation
is recorded rather than papered over (D-05).

`inpaint` and `upscale` are deliberately absent: unevenly supported across
providers and unnecessary to prove the physical pipeline (spec 8.1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from PIL import Image


@runtime_checkable
class ImageProvider(Protocol):
    name: str

    def generate(self, brief: dict) -> Image.Image:
        """Produce artwork from a structured brief."""
        ...

    def edit(self, image: Image.Image, instruction: str) -> Image.Image:
        """Modify existing artwork according to an instruction."""
        ...


class ProviderUnavailable(RuntimeError):
    """Raised when a provider cannot service a request."""


def load_image(path: str | Path) -> Image.Image:
    path = Path(path)
    if not path.is_file():
        raise ProviderUnavailable(f"No such image: {path}")
    return Image.open(path).convert("RGBA")
