import argparse
import importlib.util
import sys

import untangle

from xhb2beancount import convert, overwrite_config, print_dicts

parser = argparse.ArgumentParser(
    prog='xhb2beancount',
    description="Convert Homebank files to Beancount format.",
)


def untangle_file(filename):
    try:
        with open(filename, mode='rt') as file:
            xml = untangle.parse(file)
            xml.homebank
            return xml
    except Exception as ex:
        msg = "Invalid Homebank file"
        raise argparse.ArgumentTypeError(msg) from ex


def config_file(filename):
    spec = importlib.util.spec_from_file_location('config', filename)

    if spec is None:
        msg = "Config file is not a valid Python file"
        raise argparse.ArgumentTypeError(msg)

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    return mod


parser.add_argument('object', help="Homebank filename",
                    type=untangle_file, metavar='filename')
parser.add_argument('--config', '-c', help="Python config file",
                    type=config_file, default=None)
parser.add_argument('--print-config-dicts', '-p',
                    help="Print Homebank rename dictionaries",
                    action='store_true')


def main():
    args = parser.parse_args()

    if args.config:
        overwrite_config(args.config)

    if args.print_config_dicts:
        print_dicts(args.object, output=sys.stdout)
    else:
        beancount = convert(args.object)
        beancount.print(sys.stdout)
