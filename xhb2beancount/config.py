import datetime


DEFAULT_DATE = datetime.date(1970, 1, 1)
DEFAULT_PAD_DATE = datetime.date(1970, 1, 2)
DEFAULT_BALANCE_DATE = datetime.date(1970, 1, 3)

DEFAULT_FLAG = '*'

ASSETS_ACCOUNT = 'Assets'
EXPENSE_ACCOUNT = 'Expenses'
INCOME_ACCOUNT = 'Income'
OPENING_BALANCE_ACCOUNT = 'Equity:Opening-Balances'

ACCOUNTS_DICT = {
    'Something': 'Something-Else',
}

TAGS_DICT = {
    'tag': 'my-tag',
}

CATEGORIES_DICT = {
    '(none)': 'None',
}

PAYEE_DICT = {
}

PREFER_POSITIVE_AMOUNTS = True
REMOVE_EMPTY_CATEGORIES = True
