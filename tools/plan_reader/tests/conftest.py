"""Shared fixtures for tools/plan_reader tests."""

import pytest

_FT = 0.3048
_IN = 0.0254


@pytest.fixture
def ft():
    """Feet-to-metres conversion constant."""
    return _FT


@pytest.fixture
def inch():
    """Inches-to-metres conversion constant."""
    return _IN


@pytest.fixture
def sample_extracted():
    """Typical set of vision-extracted dimensions (metres)."""
    return [3.810, 2.438, 0.914]


@pytest.fixture
def sample_annotated():
    """Corresponding annotated reference dimensions (metres)."""
    return [3.810, 2.438, 0.914]
