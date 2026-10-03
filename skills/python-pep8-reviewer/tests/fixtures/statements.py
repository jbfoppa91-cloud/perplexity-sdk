"""Docstring is allowed before imports."""

from __future__ import annotations

__all__ = ["Case"]

import os
import unittest

try:
    import yaml
except ImportError:
    yaml = None

LOOKUP = {"a": 1, "b": [1, 2][0:1]}


class Case(unittest.TestCase):

    def setUp(self):
        self.value = os.sep

    def test_it(self):
        try:
            pass
        except:
            pass
        if self.value: print(self.value)
        else: pass
        fn = lambda: 1  # kept as a lambda on purpose
        return fn


def annotated(a: int, b: dict[str, int] = None) -> dict[str, int]:
    """Annotations use colons that are not E701."""
    x: int = 1
    for i in range(a): x += i
    with open(os.devnull) as fh: fh.read()
    return {"k": x if a else b}


while False: pass
