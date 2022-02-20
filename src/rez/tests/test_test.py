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
import io
import os
import platform
import shlex
import sys


from rez import exceptions as exceptions_, resolved_context
from rez.cli import _main, test
from rez.tests import util
from rez.vendor import wurlitzer

_SUCCESS_CODE = 0


class _Base(util.TestBase):
    """A bootstrap class for unittest classes in this module."""

    @classmethod
    def setUpClass(cls):
        """Save the install path where Rez packages should be sourced from."""
        cls.settings = dict()  # Needed for :class:`.util.TestBase`
        cls._install_path = cls.data_path("packages", "rez_test_packages")


class TestInteractiveGeneral(_Base):
    """Ensure ``rez-test --interactive`` generally works as expected."""

    def test_invalid_resolve(self):
        """Fail gracefully if the combination of tests fails to resolve."""
        with self.assertRaises(exceptions_.ResolvedContextError):
            _test_shell(
                "test variants_package python_2_test python_3_test --interactive",
                packages_path=[self._install_path],
            )

        with self.assertRaises(exceptions_.ResolvedContextError):
            stdout = _test_shell(
                "test variants_package --interactive",
                packages_path=[self._install_path],
            )

    def test_pre_test_commands(self):
        """Ensure a package's pre_test_commands is run, if it is defined."""
        stdout, _ = _test_shell(
            "test pre_test_package --variant 0 --interactive",
            packages_path=[self._install_path],
            variable="IS_FOO_TEST",
        )

        self.assertEqual("yep", stdout)

    def test_pre_test_commands_none(self):
        """Ensure a package runs even if it does not define pre_test_commands."""
        _test_shell(
            "test variants_package python_2_test --variant 0 --interactive",
            packages_path=[self._install_path],
        )

    def test_unknown_tests(self):
        """Prevent --interactive if a given test name is not already registered."""
        with self.assertRaises(exceptions_.PackageTestError):
            _test_shell(
                "test variants_package does_not_exist --interactive",
                packages_path=[self._install_path],
            )

    def test_variant_without_interactive(self):
        """Make sure --variant is only used with --interactive."""
        with _silence(), self.assertRaises(SystemExit) as result:
            _test_shell(
                "test variants_package --variant 0",
                packages_path=[self._install_path],
            )

        self.assertEqual(test.VARIANT_WITHOUT_INTERACTIVE_EXIT_CODE, result.exception.code)


class TestInteractiveVariants(_Base):
    """Ensure ``rez-test --interactive`` works with ``--variant``."""

    def test_explicit(self):
        """Asking for a specific variant should carry over into the test environment."""
        variant_0_stdout, _ = _test_shell(
            "test variants_package_simple --variant 0 --interactive",
            packages_path=[self._install_path],
            variable="REZ_VARIANTS_PACKAGE_SIMPLE_VARIANT_INDEX"
        )

        variant_1_stdout, _ = _test_shell(
            "test variants_package_simple --variant 1 --interactive",
            packages_path=[self._install_path],
            variable="REZ_VARIANTS_PACKAGE_SIMPLE_VARIANT_INDEX"
        )

        self.assertEqual("0", variant_0_stdout)
        self.assertEqual("1", variant_1_stdout)

    def test_implied_001(self):
        """Get the first found variant (if any) if no variant is specified."""
        stdout, _ = _test_shell(
            "test variants_package_simple --interactive",
            packages_path=[self._install_path],
            variable="REZ_VARIANTS_PACKAGE_SIMPLE_VARIANT_INDEX"
        )

        self.assertEqual("0", stdout)

    def test_implied(self):
        """Get the base Rez package when no variant exists."""
        stdout, _ = _test_shell(
            "test pre_test_package --interactive",
            packages_path=[self._install_path],
            variable="REZ_PRE_TEST_PACKAGE_VARIANT_INDEX"
        )

        self.assertEqual("", stdout)

    def test_invalid_explicit_test(self):
        """Fail --interactive & --variant if a specified test is not compatible.

        ``--variant 0`` uses "python-2" but "python_3_test" uses "python-3"
        Therefore, we fail early before the context gives unexpected results.

        """
        with self.assertRaises(exceptions_.ResolvedContextError):
            _test_shell(
                "test variants_package python_3_test --variant 0 --interactive",
                packages_path=[self._install_path],
            )

    def test_invalid_missing_variant(self):
        """Fail --interactive if an explicit --variant is set for a package without any."""
        with self.assertRaises(exceptions_.PackageTestError):
            _test_shell(
                "test pre_test_package --variant 1 --interactive",
                packages_path=[self._install_path],
            )

    def test_invalid_selection(self):
        """Fail --interactive when --variant points to a non-existent variant."""
        with self.assertRaises(exceptions_.PackageTestError):
            _test_shell(
                "test variants_package_simple --variant 2 --interactive",
                packages_path=[self._install_path],
            )


@contextlib.contextmanager
def _override_execute_shell(variable="REZ_RESOLVE"):
    """Change Rez's :meth:`.ResolvedContext.execute_shell` to print.

    Yields:
        callable: The overwritten
            :meth:`rez.resolved_context.ResolvedContext.execute_shell` method.

    """

    def _simulate_non_interactive(kwargs):
        system = platform.system()
        output = kwargs.copy()

        if system == "Windows":
            output["command"] = "echo %{variable}%".format(variable=variable)
        elif system == "Linux":
            output["command"] = "echo ${variable}".format(variable=variable)
        else:
            raise NotImplementedError(
                'System "{system}" is not supported yet.'.format(system=system)
            )

        output["block"] = True

        return output

    def _wrap(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            """Append a command to print the resolved packages, then run ``function``."""
            kwargs = _simulate_non_interactive(kwargs)

            return function(*args, **kwargs)

        return wrapper

    original = resolved_context.ResolvedContext.execute_shell

    try:
        resolved_context.ResolvedContext.execute_shell = _wrap(
            resolved_context.ResolvedContext.execute_shell
        )

        yield
    finally:
        resolved_context.ResolvedContext.execute_shell = original


@contextlib.contextmanager
def _silence():
    """Prevent stdout / stderr from printing and store them in streams, instead."""
    with wurlitzer.pipes() as (stdout, stderr):
        try:
            yield stdout, stderr
        finally:
            atexit.register(functools.partial(stdout.close))
            atexit.register(functools.partial(stderr.close))


def _test_shell(command, packages_path=tuple(), variable="REZ_RESOLVE"):
    """Simulate an interactive shell and get an output variable.

    Args:
        command (str):
            The raw terminal request to run. e.g. "(rez-)test foo bar", but
            within the "(rez-)" part.
        packages_path (container[str], optional):
            Override paths used to search for a Rez package.
        variable (str, optional):
            An environment variable to print and return as stdout.

    Returns:
        tuple[str, str]: The environment variable output + any potential errors.

    """
    with _override_execute_shell(variable=variable):
        stdout, stderr = _test(command, packages_path=packages_path)
        cleaned_stdout = stdout.splitlines()[-1]

        return cleaned_stdout, stderr


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

    run_command, _ = _main.get_command_details(subcommand, argv=parts)

    with _silence() as (stdout, stderr):
        try:
            run_command()
        except SystemExit as error:
            # Since Rez's CLI functions don't separate their function logic
            # from sys.exit / CLI logic, we have to catch and handle "okay"
            # SystemExit calls.
            #
            if error.code:
                # A non-null error is bad. Re-raise the exception.
                raise

    output = stdout.read()
    error = stderr.read()

    return output, error
