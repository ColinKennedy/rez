import atexit
import functools
import os
import shutil
import tempfile
import unittest

from rez.cli import _main
from rez.cli import test
from rez.utils import filesystem


class TestUnspecifiedPackage(unittest.TestCase):
    """Determine the behavior if no package is given during a ``rez-test`` command."""

    def test_default_tests(self):
        """If the user doesn't specify tests to run, make sure the defaults run."""
        raise ValueError()

    def test_explicit_tests(self):
        """If the user asks for specific tests, run them."""
        raise ValueError()

    def test_unspecified_prefers_local_definition(self):
        """Use the local Rez package even if an installed Rez package exists."""
        raise ValueError()

    def test_invalid_package_definition(self):
        """Fail + exit early if the the local package has an issue of some sort."""
        raise ValueError()

    def test_permission_issue(self):
        """Exit rez-test early if the user does not have directory read permissions."""
        directory = _make_directory("_TestUnspecifiedPackage_test_permission_issue")

        with filesystem.retain_cwd():
            os.chdir(directory)

        raise ValueError()

    def test_not_found(self):
        """Exit rez-test early because no Rez package could be found."""
        directory = tempfile.mkdtemp(suffix="_TestUnspecifiedPackage_test_not_found")
        _delete_directory_later(directory)

        with filesystem.retain_cwd():
            os.chdir(directory)

            with self.assertRaises(SystemError) as error:
                _main.run("test")

            self.assertEqual(error.return_code == test.PACKAGE_NOT_FOUND_EXIT_CODE)


def _delete_directory_later(directory):
    atexit.register(functools.partial(shutil.rmtree, directory))


def _make_directory(name):
    directory = tempfile.mkdtemp(suffix=name)
    _delete_directory_later(directory)

    return directory
