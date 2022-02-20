# Copyright Contributors to the Rez project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
test that ``rez-test`` works as expected.
"""
import atexit
import contextlib
import functools
import os
import shlex
import shutil
import stat
import sys
import tempfile
import textwrap
import unittest

from rez import build_process, build_system
from rez.cli import _main, test
from rez.utils import filesystem


_SUCCESS_CODE = 0
_PACKAGE_TEXT = textwrap.dedent(
    """\
    name = "some_package"

    version = "1.0.0"

    build_command = ""

    tests = {
        "test_1": "echo test_1",
        "test_2": "echo test_2",
    }
    """
)


class TestUnspecifiedPackage(unittest.TestCase):
    """Determine the behavior if no package is given during a ``rez-test`` command."""

    @classmethod
    def setUpClass(cls):
        """Create a base Rez package and install it, for use in other tests."""
        cls._developer_directory = _make_quick_package()  # A ready-made Rez developer package

        with filesystem.retain_cwd():
            os.chdir(cls._developer_directory)

            install_path = _build_package(cls._developer_directory)

        cls._installed_directory = install_path

    def test_default_tests(self):
        """If the user doesn't specify tests to run, make sure the defaults run."""
        with filesystem.retain_cwd():
            os.chdir(self._developer_directory)

            with self.assertRaises(SystemExit) as result:
                _test("test .", packages_path=[self._installed_directory])

        self.assertEqual(result.exception.code, _SUCCESS_CODE)

    def test_explicit_tests(self):
        """If the user specifies tests to run, run those."""
        with filesystem.retain_cwd():
            os.chdir(self._developer_directory)

            with self.assertRaises(SystemExit) as result:
                _test("test . test_1", packages_path=[self._installed_directory])

        self.assertEqual(result.exception.code, _SUCCESS_CODE)

    def test_invalid_package_definition(self):
        """Fail + exit early if the the local package has an issue of some sort."""
        bad_text = _PACKAGE_TEXT + "\n{}().{}"
        directory = _make_quick_package(text=bad_text)

        with filesystem.retain_cwd():
            os.chdir(directory)

            with self.assertRaises(SystemExit) as result:
                _test("test .", packages_path=[self._installed_directory])

        self.assertEqual(test.PACKAGE_NOT_FOUND_EXIT_CODE, result.exception.code)

    def test_invalid_test(self):
        """Fail execution if the specified test does not exist."""
        with filesystem.retain_cwd():
            os.chdir(self._developer_directory)

            with self.assertRaises(SystemExit) as result:
                _test("test . does_not_exist", packages_path=[self._installed_directory])

        self.assertEqual(1, result.exception.code)

    def test_permission_issue(self):
        """Exit rez-test early if the user does not have directory read permissions."""
        directory = _make_quick_package()  # A ready-made Rez developer package

        # 1. Run a test command once to ensure that it otherwise is valid
        with filesystem.retain_cwd():
            os.chdir(directory)

            with self.assertRaises(SystemExit) as ordinary_result:
                _test("test .", packages_path=[self._installed_directory])

        self.assertEqual(_SUCCESS_CODE, ordinary_result.exception.code)

        # 2. Run the same command, this time with a PWD with bad permissions
        with filesystem.retain_cwd():
            os.chdir(directory)

            # Forcibly change `directory` to be not executable while the user
            # is still cd'ed into it. Which means a test command which would
            # normally have not failed now will.
            #
            os.chmod(directory, stat.S_IRUSR | stat.S_IWUSR)

            with self.assertRaises(SystemExit) as bad_result:
                try:
                    _test("test .", packages_path=[self._installed_directory])
                finally:
                    os.chmod(directory, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        self.assertEqual(test.PACKAGE_NOT_FOUND_EXIT_CODE, bad_result.exception.code)

    def test_not_found(self):
        """Exit rez-test early because no Rez package could be found."""
        directory = tempfile.mkdtemp(suffix="_TestUnspecifiedPackage_test_not_found")
        _delete_directory_later(directory)

        with filesystem.retain_cwd():
            os.chdir(directory)

            with self.assertRaises(SystemExit) as result:
                _test("test .")

        self.assertEqual(test.PACKAGE_NOT_FOUND_EXIT_CODE, result.exception.code)


def _build_package(directory):
    """Build the Rez package under ``directory``.

    Args:
        directory (str): The directory on-disk to a developer Rez package to build.

    Returns:
        str: The temporary directory where the package was installed into.

    """
    with _silence():
        install_path = _make_directory("_build_package_install_path")
        system = build_system.create_build_system(directory)
        builder = build_process.create_build_process(
            process_type="local",
            build_system=system,
            working_dir=directory,
        )

        builder.build(
            install_path=install_path,
            clean=True,
            install=True,
        )

        return install_path


def _delete_directory_later(directory):
    """Schedule ``directory`` to be deleted.

    Args:
        directory (str): A folder on-disk which is deleted once Python exits.

    """
    atexit.register(functools.partial(shutil.rmtree, directory))


def _make_directory(name):
    """Create a temporary directory containing ``name`` in its path.

    Args:
        name (str): Some unique text used to identify the temporary directory.

    Returns:
        str: The absolute path to the generated directory.

    """
    directory = tempfile.mkdtemp(suffix=name)
    _delete_directory_later(directory)

    return directory


def _make_quick_package(text=_PACKAGE_TEXT):
    """Create a Rez package using ``text`` for unittesting.

    Args:
        text (str, optional): The raw Python source code used for created package.

    Returns:
        str: The absolute path to directory containing the created package.

    """
    directory = _make_directory("_make_quick_package")

    with open(os.path.join(directory, "package.py"), "w") as handler:
        handler.write(text)

    return directory


@contextlib.contextmanager
def _retain_argv():
    """Save + Restore :attr:`sys.argv` once the Python context exits."""
    arguments = sys.argv[:]

    try:
        yield
    finally:
        sys.argv[:] = arguments


@contextlib.contextmanager
def _silence():
    """Hide stdout and stderr printouts for the duration of this Python context."""
    # Initialize the streams
    new_stderr = open(os.devnull, "w")
    new_stdout = open(os.devnull, "w")
    original_stderr = sys.stderr
    original_stdout = sys.stdout

    # Override the streams
    sys.stderr = new_stderr
    sys.stdout = new_stdout

    try:
        yield
    finally:
        # Close the pending streams
        sys.stderr.close()
        sys.stdout.close()

        # Restore the original streams
        sys.stderr = original_stderr
        sys.stdout = original_stdout


def _test(command, packages_path=tuple()):
    """Simulate a user calling ``rez-test`` from the terminal.

    Args:
        command (str):
            The raw terminal request to run. e.g. "(rez-)test foo bar", but
            within the "(rez-)" part.
        packages_path (container[str], optional):
            Override paths used to search for a Rez package.

    """
    parts = shlex.split(command)

    if packages_path:
        parts.extend(["--paths", *packages_path])

    subcommand = parts[0]

    with _retain_argv(), _silence():
        sys.argv = parts
        _main.run(subcommand)
