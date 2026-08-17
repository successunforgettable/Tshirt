"""FileProvider — artwork supplied by the operator from any source.

Not a test stub. This is the escape hatch that keeps the entire deterministic
print pipeline usable with zero AI availability: no API key, no egress, no
provider account. If a hosted provider becomes unreachable, its key is revoked,
or its model changes, print preparation continues unaffected (D-05).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from .base import ProviderUnavailable, load_image


class FileProvider:
    """Serves artwork from local files rather than a model."""

    name = "file"

    def __init__(self, source: str | Path | None = None):
        self.source = Path(source) if source else None

    def generate(self, brief: dict) -> Image.Image:
        source = brief.get("source_image", self.source)
        if source is None:
            raise ProviderUnavailable(
                "FileProvider needs a source image: pass source_image in the brief "
                "or a source path at construction."
            )
        return load_image(source)

    def edit(self, image: Image.Image, instruction: str) -> Image.Image:
        raise ProviderUnavailable(
            f"FileProvider cannot edit artwork (requested: {instruction!r}). "
            "Supply a revised file instead."
        )
