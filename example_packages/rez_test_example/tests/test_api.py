"""Make sure :mod:`rez_test_example.Api` works as expected."""

import unittest

from rez_test_example import api


class IsItertype(unittest.TestCase):
    """Make sure :mod:`rez_test_example.Api` works as expected."""

    def test_iterable_invalids(self):
        """Fail when a non-iterable type is given."""
        self.assertFalse(api.is_itertype(1))
        self.assertFalse(api.is_itertype(None))

    def test_iterable_iterator(self):
        """Pass if any iterator is given."""
        self.assertTrue(api.is_itertype(_iterate(0)))
        self.assertTrue(api.is_itertype(_iterate(10)))

    def test_iterable_list(self):
        """Pass if any list is given."""
        self.assertTrue(api.is_itertype([]))  # An empty list is still True
        self.assertTrue(api.is_itertype(["A string"]))

    def test_iterable_string(self):
        """Fail when a string is used."""
        self.assertFalse(api.is_itertype("Some string"))


def _iterate(value):
    """Create a quick generator for our unittests."""
    for index in range(value):
        yield index
