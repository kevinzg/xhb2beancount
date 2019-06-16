import argparse
import importlib.util
import sys

import untangle

from xhb2beancount import convert

parser = argparse.ArgumentParser(
    prog='xhb2beancount',
    description="Convert Homebank files to Beancount format.",
)


def untangle_file(filename):
    try:
        return untangle.parse(filename)
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
parser.add_argument('--config', help="Python config file",
                    type=config_file, default=None)


def main():
    args = parser.parse_args()

    beancount = convert(args.object, args.config)
    beancount.print(sys.stdout)
