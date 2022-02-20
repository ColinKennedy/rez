name = "pre_test_package"

version = "1.0.0"

tests = {
    "foo": "echo foo",
    "bar": "echo bar",
}

timestamp = 1463350552


def pre_test_commands():
    if "foo" in {test.name for test in tests}:
        env.IS_FOO_TEST = "yep"
