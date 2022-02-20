name = "variants_package"

version = "1.0.0"

tests = {
    "foo": "echo foo",
    "bar": "echo bar",
    "python_2_test": {
        "command": "echo python 2",
        "requires": ["python-2"],
    },
    "python_3_test": {
        "command": "echo python 3",
        "requires": ["python-3"],
    },
}

variants = [["python-2"], ["python-3"]]

timestamp = 1463350552
