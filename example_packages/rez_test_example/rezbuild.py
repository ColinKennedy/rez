#!/usr/bin/env python

"""Copy the Python files and / or documentation.

Python files will always be copied. But documentation is only copied when it's
generated (which typically happens just before release).

"""

import os
import shutil


def _remove(path):
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def _build(source, build, install):

    def _build_python(source, install):
        for folder in ["python"]:
            full_source = os.path.join(source, folder)
            full_destination = os.path.join(install, folder)

            _remove(full_destination)
            shutil.copytree(full_source, full_destination)

    _build_python(source, install)


if __name__ == '__main__':
    _build(
        source=os.environ['REZ_BUILD_SOURCE_PATH'],
        build=os.environ['REZ_BUILD_PATH'],
        install=os.environ['REZ_BUILD_INSTALL_PATH'],
    )
