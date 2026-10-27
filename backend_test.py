"""Compatibility entry point for the deterministic offline suite.

Run with the repository virtual-environment Python from any working directory.
No hosted preview, API key, real match ID or report export is used.
"""
from pathlib import Path
import sys
import unittest

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    suite = unittest.defaultTestLoader.discover(str(root / 'tests'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
