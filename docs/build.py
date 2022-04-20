# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import contextlib
import itertools
import os
import re
import shutil
import subprocess
import sys
import tempfile

from sphinx.cmd import build as sphinx_build
from sphinx.ext import apidoc


THIS_FILE = os.path.abspath(__file__)
THIS_DIR = os.path.dirname(THIS_FILE)
REZ_SOURCE_DIR = os.getenv("REZ_SOURCE_DIR", os.path.dirname(THIS_DIR))
REQUIREMENTS = (
    "sphinx_rtd_theme",
    "Qt.py>=1",  # Needed for :mod:`rezgui`
    "pysvn>=0.1",  # Needed for :mod:`rezplugins.release_vcs`
    REZ_SOURCE_DIR,
)
DEST_DIR = os.path.join("docs", "_build")
PIP_PATH_REGEX = re.compile(r"'([^']+)' which is not on PATH.")

_SPHINX_EXTENSION = ".rst"

# Arbitrary folders which we probably don't want to expose API documentation for
_EXCLUDED_API_DIRECTORIES = (
    "src/build_utils",
    "src/rez/tests",
    "src/rez/vendor",
    "src/support",
)


# TODO : Remove this later
class CliParser(argparse.ArgumentParser):
    """Parser flags, using global variables as defaults."""

    INIT_DEFAULTS = {
        "prog": "build",
        "description": "Build Sphinx Python API docs",
    }

    def __init__(self, **kwargs):
        """Setup default arguments and parser description/program name.

        If no parser description/program name are given, default ones will
        be assigned.

        Args:
            kwargs (dict[str]):
                Same key word arguments taken by
                ``argparse.ArgumentParser.__init__()``
        """
        for key, value in self.INIT_DEFAULTS.items():
            kwargs.setdefault(key, value)
        super(CliParser, self).__init__(**kwargs)

        self.add_argument(
            "--api-source",
            default=os.path.join(REZ_SOURCE_DIR, "src"),
            help="The folder where all Rez-related Python files live.",
        )

        self.add_argument(
            "--api-destination",
            default=os.path.join(REZ_SOURCE_DIR, "docs", "api"),
            help="The folder where auto-generated sphinx-apidoc .rst files will be written to."
        )

        self.add_argument(
            "--no-docker",
            action="store_false",
            dest="docker",
            help="Don't run build processes inside Docker container.",
        )
        self.add_argument(
            "requirement",
            nargs="*",
            help="Additional packages to pip install.",
        )


def construct_docker_run_args():
    """Create subprocess arguments list for running this script inside docker.

    Returns:
        list[str]: Arguments list for ``subprocess.call()``.
    """
    docker_args = ["docker", "run", "--interactive", "--rm"]

    if os.sys.stdin.isatty() and os.sys.stdout.isatty():
        docker_args.append("--tty")

    if os.name == "posix":
        user_group_ids = os.getuid(), os.getgid()
        docker_args += ["--user", ":".join(map(str, user_group_ids))]

    docker_args += [
        "--workdir",
        REZ_SOURCE_DIR,
        "--volume",
        ":".join([REZ_SOURCE_DIR, REZ_SOURCE_DIR]),
        "python:{v.major}.{v.minor}".format(v=os.sys.version_info),
        "python",
        THIS_FILE,
        "--no-docker",
    ]

    return docker_args


def print_call(cmdline_args, *print_args, **print_kwargs):
    """Print command line call for given arguments.


    Args:
        cmdline_args (list): Command line arguments to print for.
        print_args (dict): Additional arguments for print function.
        print_kwargs (dict): Keyword arguments for print function.
    """
    width = os.getenv("COLUMNS", 80)
    out_file = print_kwargs.setdefault("file", os.sys.stdout)
    message = "{:=^{width}}{nl}{}{nl:=<{width}}".format(
        " Calling ", subprocess.list2cmdline(cmdline_args), nl=os.linesep, width=width
    )
    print(message, *print_args, **print_kwargs)
    out_file.flush()


def path_with_pip_scripts(install_stderr, path_env=None):
    """Create new PATH variable with missing pip scripts paths added to it.

    Args:
        install_stderr (str): stderr output from pip install command.
        path_env (str): Custom PATH env value to start off with.

    Returns:
        str: New PATH variable value.
    """
    if path_env is None:
        path_env = os.getenv("PATH", "")
    paths = path_env.split(os.pathsep)

    for match in PIP_PATH_REGEX.finditer(install_stderr):
        script_path = match.group(1)
        if script_path not in paths:
            paths.append(script_path)

    return os.pathsep.join(paths)


def _clear_rst_files(directory):
    for name in os.listdir(directory):
        if not name.endswith(_SPHINX_EXTENSION):
            continue

        os.remove(os.path.join(directory, name))


def _install_pip_packages(requirements):
    # Run pip install for required docs building packages
    for requirement in itertools.chain(REQUIREMENTS, requirements):
        # TODO : replace with import + call
        pip_args = ["pip", "install", "--user", requirement]
        subprocess.check_call(pip_args, env=os.environ)


@contextlib.contextmanager
def _keep_environment():
    original = os.environ.copy()

    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


def _run_sphinx_apidoc(source, destination):
    if os.path.isdir(destination):
        _clear_rst_files(destination)

    command = ["--separate", "--output-dir", destination, source]
    command.extend(_EXCLUDED_API_DIRECTORIES)

    apidoc.main(command)


def _run_sphinx_build(destination):
    # Run sphinx-build docs, falling back to use sphinx-build.exe
    build_args = ["docs", destination]

    try:
        sphinx_build.main(build_args)
    except SystemExit as error:
        return error.code

    return 0


def _run_without_docker(requirements, api_source, api_destination):
    environment = os.environ.copy()

    # Fake user's $HOME in container to fix permission issues
    if os.name == "posix" and os.path.expanduser("~") == "/":
        environment["HOME"] = tempfile.mkdtemp()

    try:
        _run_sphinx_apidoc(api_source, api_destination)
    except SystemExit as error:
        return error.code

    with _keep_environment():
        os.environ.update(environment)

        return _run_sphinx_build(DEST_DIR)


def main():
    """Parse the user's input and build Sphinx documentation."""
    args = CliParser().parse_args()

    if args.docker:
        docker_args = construct_docker_run_args() + args.requirement
        print_call(docker_args)

        sys.exit(subprocess.call(docker_args))

    sys.exit(_run_without_docker(args.requirement, args.api_source, args.api_destination))


if __name__ == "__main__":
    main()
