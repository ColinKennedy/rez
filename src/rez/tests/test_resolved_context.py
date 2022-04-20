"""Ensure specific functionality of :mod:`rez.resolved_context` works."""

import copy
import contextlib
import os
import platform

from rez.cli import _main
from rez.config import _replace_config, config
from rez.tests import util


class FavorPaths(util.TestBase):
    """Make sure ``--favor-paths`` works as expected."""

    @classmethod
    def setUpClass(cls):
        """Keep track of the top-level directory installed Rez packages live."""
        super(FavorPaths, cls).setUpClass()

        cls._root = cls.data_path("builds", "favor_paths_packages")

    def test_cli_explicit(self):
        """Force Rez to use packages found in ``--favor-paths``."""
        raise ValueError()

    def test_cli_implicit(self):
        """Force Rez to use local_packages_path from ``--favor-paths``."""
        local_packages_path = os.path.join(self._root, "example_local")
        installed = os.path.join(self._root, "regular_installed")
        paths = (os.pathsep).join([installed, local_packages_path])

        with _make_local_configuration(local_packages_path):
            _run_test(
                [
                    "env",
                    "foo",
                    "--favor-paths",
                    "--paths={paths}".format(paths=paths),
                ],
                "REZ_FOO_VERSION",
            )

        raise ValueError()

    def test_empty(self):
        """Ensure an empty directory does not affect Rez resolves."""
        raise ValueError()

    def test_non_existent(self):
        """Fail early if a provided path doesn't exist or isn't a directory."""
        raise ValueError()

    def test_not_provided(self):
        """Make sure not providing ``--favor-paths`` works as expected."""
        raise ValueError()


@contextlib.contextmanager
def _make_local_configuration(path):
    configuration = config.copy()
    configuration.local_packages_path = path

    with _override_config():
        _replace_config(configuration)

        yield


@contextlib.contextmanager
def _override_config():
    original = config.copy()

    try:
        yield
    finally:
        _replace_config(original)


def _run_test(parts, name):

    def _to_variable(name):
        if platform.system() == "Windows":
            return "%{name}%".format(name=name)

        return "${name}".format(name=name)

    parts = copy.copy(parts)
    parts.extend(["--", "echo", _to_variable(name)])
    subcommand = parts[0]

    command, _ = _main.parse_command(subcommand, argv=parts)

    try:
        command()
    except SystemExit as error:
        if error.code != 0:
            raise
