# xhb2beancount

Homebank to Beancount converter.

## Install

I recommend using [pipx](https://pipxproject.github.io/pipx/).

```sh
pipx install xhb2beancount
```

Or just create a virtualenv and run `pip install xhb2beancount`.

## Usage

```sh
xhb2beancount file.xhb > file.beancount
```

If you have beancount installed you can format it with bean-format.

```sh
xhb2beancount file.xhb | bean-format -c 78 > file.beancount
```

You can customize the conversion passing a config file as an argument.

```sh
xhb2beancount --config config.py file.xhb
```

Copy the [default config file](https://github.com/kevinzg/xhb2beancount/blob/master/xhb2beancount/config.py) and edit it to suit your needs.

You can also use the option `--print-config-dicts` to print the categories, accounts, payees and tags
from your Homebank file as dictionares and copy them to your config file.

```sh
xhb2beancount file.xhb --print-config-dicts
```
