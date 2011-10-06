#!/usr/bin/env python

"""
Runs unit and integration tests.
"""

import unittest
import test.version

if __name__ == '__main__':
  suite = unittest.TestLoader().loadTestsFromTestCase(test.version.TestVerionFunctions)
  unittest.TextTestRunner(verbosity=2).run(suite)
