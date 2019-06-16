# xhb2beancount

Homebank to Beancount converter.

## Install

```sh
pipx install xhb2beancount
```

## Usage

```sh
xhb2beancount file.xhb > file.beancount
```

If you have beancount installed you can format it with bean-format.

```sh
xhb2beancount file.xhb | bean-format -c 78 > file.beancount
```
