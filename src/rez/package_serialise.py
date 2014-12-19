from rez.vendor import yaml
from rez.serialise import FileFormat
from rez.package_resources_ import help_schema
from rez.vendor.schema.schema import Schema, Optional, And, Use
from rez.vendor.version.version import Version
from rez.utils.data_utils import SourceCode
from rez.utils.formatting import PackageRequest, indent, dict_to_attributes_code
from rez.utils.schema import Required
from rez.utils.yaml import dump_yaml
from pprint import pformat


# preferred order of keys in a package definition file
package_key_order = [
    'name',
    'version',
    'description',
    'authors',
    'tools',
    'requires',
    'build_requires',
    'private_build_requires',
    'variants',
    'commands',
    'pre_commands',
    'post_commands',
    'help',
    'config',
    'uuid']


package_request_schema = And(PackageRequest, Use(str))


# package serialisation schema
package_serialise_schema = Schema({
    Required("name"):                   basestring,
    Optional("version"):                And(Version, Use(str)),
    Optional("description"):            basestring,
    Optional("authors"):                [basestring],
    Optional("tools"):                  [basestring],

    Optional('requires'):               [package_request_schema],
    Optional('build_requires'):         [package_request_schema],
    Optional('private_build_requires'): [package_request_schema],
    Optional('variants'):               [[package_request_schema]],

    Optional('pre_commands'):           SourceCode,
    Optional('commands'):               SourceCode,
    Optional('post_commands'):          SourceCode,

    Optional("help"):                   help_schema,
    Optional("uuid"):                   basestring,
    Optional("config"):                 dict,

    Optional(basestring):               object
})


def dump_package_data(data, buf, format_=FileFormat.py, skip_attributes=None):
    """Write package data to `buf`.

    Args:
        data (dict): Data source - must conform to `package_serialise_schema`.
        buf (file-like object): Destination stream.
        format_ (`FileFormat`): Format to dump data in.
        skip_attributes (lsit of str): List of attributes to not print.
    """
    if format_ == FileFormat.txt:
        raise ValueError("'txt' format not supported for packages.")

    data_ = dict((k, v) for k, v in data.iteritems() if v is not None)
    data_ = package_serialise_schema.validate(data_)
    skip = set(skip_attributes or [])

    items = []
    for key in package_key_order:
        if key not in skip:
            value = data_.get(key)
            if value is not None:
                items.append((key, value))

    dump_func = dump_functions[format_]
    dump_func(items, buf)


def _commented_old_command_annotations(sourcecode):
    lines = sourcecode.source.split('\n')
    for i, line in enumerate(lines):
        if line.startswith("comment('OLD COMMAND:"):
            lines[i] = "# " + line
    source = '\n'.join(lines)
    return SourceCode(source)


def _dump_package_data_yaml(items, buf):
    for i, (key, value) in enumerate(items):
        if isinstance(value, SourceCode) \
                and key in ("commands", "pre_commands", "post_commands"):
            value = _commented_old_command_annotations(value)

        d = {key: value}
        txt = dump_yaml(d)
        print >> buf, txt
        if i < len(items) - 1:
            print >> buf, ''


def _dump_package_data_py(items, buf):
    for i, (key, value) in enumerate(items):
        if key == "description":
            # description is a triple-quoted string
            quoted_str = '"""\n%s\n"""' % value
            txt = "description = \\\n%s" % indent(quoted_str)
        elif key == "config":
            # config is a scope context
            txt = dict_to_attributes_code(dict(config=value))
        elif isinstance(value, SourceCode):
            # source code becomes a python function
            if key in ("commands", "pre_commands", "post_commands"):
                value = _commented_old_command_annotations(value)
            txt = "def %s():\n%s" % (key, indent(value.source))
        elif isinstance(value, list) and len(value) > 1:
            # nice formatting for lists
            lines = ["%s = [" % key]
            for j, entry in enumerate(value):
                entry_txt = pformat(entry)
                entry_lines = entry_txt.split('\n')
                for k, line in enumerate(entry_lines):
                    if j < len(value) - 1 and k == len(entry_lines) - 1:
                        line = line + ","
                    lines.append("    " + line)
            lines.append("]")
            txt = '\n'.join(lines)
        else:
            # default serialisation
            value_txt = pformat(value)
            if '\n' in value_txt:
                txt = "%s = \\\n%s" % (key, indent(value_txt))
            else:
                txt = "%s = %s" % (key, value_txt)

        print >> buf, txt
        if i < len(items) - 1:
            print >> buf, ''


dump_functions = {FileFormat.py:    _dump_package_data_py,
                  FileFormat.yaml:  _dump_package_data_yaml}
