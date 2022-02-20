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


'''
Run tests listed in a package's definition file.
'''
from __future__ import print_function


_DEVELOPER_RESERVED_NAME = "."
PACKAGE_NOT_FOUND_EXIT_CODE = 1


def _get_package_request(path):
    """Find an exact package request, given some directory on-disk.

    Args:
        path (str): A directory on-disk should have a Package definition file.

    Returns:
        str: A converted package request, e.g. "package_name==1.2.3", if any is found.

    """
    import sys

    from rez.serialise import FileFormat
    from rez.exceptions import PackageMetadataError, ResourceError
    from rez.packages_ import get_developer_package

    try:
        package = get_developer_package(path)
    except PackageMetadataError:
        options = ", ".join(
            (
                "package.{extension}".format(extension=extension)
                for format_ in FileFormat
                for extension in format_.value
            )
        )

        print(
            'Path "{path}" contains no Rez package.\n'
            'Make sure there at least one "{options}" file in your directory.'.format(
                path=path, options=options,
            ),
            file=sys.stderr,
        )

        return ""
    except ResourceError as error:
        print(
            'Path "{path}" found an invalid Rez package. Error:'.format(path=path),
            file=sys.stderr,
        )
        print(str(error), file=sys.stderr)

        return ""
    except PermissionError:
        print(
            'Directory "{path}" is not inspectable. No Rez package was found.'.format(
                path=path
            ),
            file=sys.stderr,
        )

        return ""

    return "{package.name}=={package.version}".format(package=package)


def _expand_request(request):
    """Convert ``request`` into a full Rez request string, if possible.

    Args:
        request (str): An initial package and/or version, or ".", indicating the current package.

    Returns:
        str: The package request, if any.

    """
    import os

    if request != _DEVELOPER_RESERVED_NAME:
        return request

    return _get_package_request(os.getcwd())


def setup_parser(parser, completions=False):
    parser.add_argument(
        "-l", "--list", action="store_true",
        help="list package's tests and exit")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="dry-run mode: show what tests would have been run, but do not "
        "run them")
    parser.add_argument(
        "-s", "--stop-on-fail", action="store_true",
        help="stop on first test failure")
    parser.add_argument(
        "--inplace", action="store_true",
        help="run tests in the current environment. Any test whose requirements "
        "are not met by the current environment is skipped")
    PKG_action = parser.add_argument(
        "--extra-packages", nargs='+', metavar="PKG",
        help="extra packages to add to test environment")
    parser.add_argument(
        "--paths", type=str, default=None,
        help="set package search path")
    parser.add_argument(
        "--nl", "--no-local", dest="no_local", action="store_true",
        help="don't load local packages")
    PKG_action = parser.add_argument(
        "PKG",
        help="package run tests on")
    parser.add_argument(
        "TEST", nargs='*',
        help="tests to run (run all if not provided)")

    if completions:
        from rez.cli._complete_util import PackageCompleter
        PKG_action.completer = PackageCompleter


def command(opts, parser, extra_arg_groups=None):
    from rez.package_test import PackageTestRunner
    from rez.config import config
    import os.path
    import sys

    # note that argparse doesn't support mutually exclusive arg groups
    if opts.inplace and (opts.extra_packages or opts.paths or opts.no_local):
        parser.error(
            "Cannot use --inplace in combination with "
            "--extra-packages/--paths/--no-local"
        )

    if opts.paths is None:
        pkg_paths = (config.nonlocal_packages_path
                     if opts.no_local else None)
    else:
        pkg_paths = opts.paths.split(os.pathsep)
        pkg_paths = [os.path.expanduser(x) for x in pkg_paths if x]

    pkg_request = _expand_request(opts.PKG)

    if not pkg_request:
        sys.exit(PACKAGE_NOT_FOUND_EXIT_CODE)

    # run test(s)
    runner = PackageTestRunner(
        package_request=pkg_request,
        package_paths=pkg_paths,
        extra_package_requests=opts.extra_packages,
        dry_run=opts.dry_run,
        stop_on_fail=opts.stop_on_fail,
        use_current_env=opts.inplace,
        verbose=2
    )

    test_names = runner.get_test_names()
    uri = runner.get_package().uri

    if not test_names:
        print("No tests found in %s" % uri, file=sys.stderr)
        sys.exit(0)

    if opts.list:
        if sys.stdout.isatty():
            print("Tests defined in %s:" % uri)

        print('\n'.join(test_names))
        sys.exit(0)

    if opts.TEST:
        run_test_names = opts.TEST
    else:
        # if no tests are explicitly specified, then run only those with a
        # 'default' run_on tag
        run_test_names = runner.get_test_names(run_on=["default"])

        if not run_test_names:
            print(
                "No tests with 'default' run_on tag found in %s" % uri,
                file=sys.stderr
            )
            sys.exit(0)

    exitcode = 0

    for test_name in run_test_names:
        if not runner.stopped_on_fail:
            ret = runner.run_test(test_name)
            if ret and not exitcode:
                exitcode = ret

    print("\n")
    runner.print_summary()
    print('')

    sys.exit(exitcode)
