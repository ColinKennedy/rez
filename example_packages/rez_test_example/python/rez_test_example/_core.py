"""An example module."""

import six


def is_itertype(item):
    """Check if some input is iterable or not.

    Have a special condition to prevent strings from returning True.

    Args:
        item (object): Some Python object to check.

    Returns:
        bool: If it is an iterable and not a string, return True.

    """
    if isinstance(item, six.string_types):
        return False

    try:
        iter(item)
    except TypeError:
        return False

    return True
