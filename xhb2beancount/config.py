import datetime

# Default dates for Beancount account openings.
DEFAULT_DATE = datetime.date(1970, 1, 1)
DEFAULT_PAD_DATE = datetime.date(1970, 1, 2)
DEFAULT_BALANCE_DATE = datetime.date(1970, 1, 3)

# Default flag for Beancount transactions.
DEFAULT_FLAG = '*'

# Default account names.
ASSETS_ACCOUNT = 'Assets'
EXPENSE_ACCOUNT = 'Expenses'
INCOME_ACCOUNT = 'Income'
OPENING_BALANCE_ACCOUNT = 'Equity:Opening-Balances'

# Homebank accounts will be renamed using this dictionary.
ACCOUNTS_DICT = {
    'Something': 'Something-Else',
}

# Homebank tags will be comma-split and renamed using this dictionary.
TAGS_DICT = {
    'tag': 'my-tag',
}

# Homebank categories will be renamed using this dictionary.
CATEGORIES_DICT = {
    '(none)': 'None',
    'Wage & Salary': 'Wage and Salary',
}

# Homebank payees will be renamed using this dictionary.
PAYEE_DICT = {
}

# Beancount accounts will be renamed using this dictionary.
BC_ACCOUNTS_DICT = {
    'Income:Wage-and-Salary:Net-Pay': 'Income:Wage-Salary:Net-Pay',
}

# Prefer positive amounts will swap the accounts and multiply the amount by -1
# if the amount is negative. It doesn't affect internal transfers.
PREFER_POSITIVE_AMOUNTS = True

# Remove empty categories will exclude unused Homebank categories.
REMOVE_EMPTY_CATEGORIES = True
