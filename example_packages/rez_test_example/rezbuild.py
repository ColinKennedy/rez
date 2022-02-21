#!/usr/bin/env python

import os
import shutil


def _remove(path):
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def build(source, install):
    for folder in ["python"]:
        full_source = os.path.join(source, folder)
        full_destination = os.path.join(install, folder)

        _remove(full_destination)
        shutil.copytree(full_source, full_destination)


if __name__ == '__main__':
    build(
        source=os.environ['REZ_BUILD_SOURCE_PATH'],
        install=os.environ['REZ_BUILD_INSTALL_PATH'],
    )
