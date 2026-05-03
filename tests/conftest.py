"""Test-suite-wide fixtures and defaults."""
from __future__ import annotations

import os


def pytest_configure(config) -> None:  # noqa: ANN001 — pytest plugin signature
    """Disable image-viewer opening during tests so generate_image flows
    don't actually launch Preview / xdg-open during unit runs."""
    os.environ.setdefault("OPEN_GENERATED_IMAGES", "false")
