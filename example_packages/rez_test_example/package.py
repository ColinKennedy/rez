name = "rez_test_example"

version = "1.0.0"

description = 'A variety of rez-test commands for the "Testing Packages" wiki section.'

authors = ["ColinKennedy"]

variants = [
    ["python-2", "six-1"],
    ["python-3"],
]

build_command = "python {root}/rezbuild.py"

tests = {
    "black_diff": {
        "command": "black --diff --check python tests",
        "requires": ["black"],
    },
    "black": {
        "command": "black python tests",
        "requires": ["black"],
        "run_on": "explicit",
    },
    "documentation": {
        "command": "sphinx-build -b html documentation build/documentation",
        "on_variants": {"value": ["python-3"], "type": "requires"},
        "requires": ["Sphinx"],
        "run_on": "pre_release",
    },
    "unittest": {
        "command": "python -m unittest discover",
        "on_variants": {"value": ["python"], "type": "requires"},
    },
}


def commands():
    import os

    env.PYTHONPATH.append(os.path.join(root, "python"))
