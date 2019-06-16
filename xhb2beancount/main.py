import sys

from xhb2beancount import convert


def main():
    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} file.xhb', file=sys.stderr)
        exit(1)

    beancount = convert(sys.argv[1])
    beancount.print(sys.stdout)
