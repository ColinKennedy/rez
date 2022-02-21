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
    "documentation": {
        "command": "sphinx-build -b html documentation/source documentation/build",
        "requires": ["Sphinx", "python-3"],
    },
    "unittest": {
        "command": "python -m unittest discover",
        "on_variants": {"value": ["python"], "type": "requires"},
    },
}


def commands():
    import os

    env.PYTHONPATH.append(os.path.join(root, "python"))
