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

You can configurate the conversion passing a config file as an argument.

```sh
xhb2beancount --config config.py file.xhb
```

Copy the [default config file](https://github.com/kevinzg/xhb2beancount/blob/master/xhb2beancount/config.py) and edit it to suit your needs.

If you have beancount installed you can format it with bean-format.

```sh
xhb2beancount file.xhb | bean-format -c 78 > file.beancount
```
