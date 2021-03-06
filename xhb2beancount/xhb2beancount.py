import datetime
import re
import sys
import warnings
from decimal import Decimal
from itertools import chain
from pprint import pformat

from beancount.core import data as bc
from beancount.parser import printer
from text_unidecode import unidecode

from . import config


class Homebank:
    INTERNAL_TRANSFER = '5'
    INCOME_FLAG = 0b10
    TAG_SEP_REGEX = re.compile(r'[\s,]')

    def __init__(self, data=None):
        self.currencies = {}
        self.accounts = {}
        self.categories = {}
        self.tags = {}
        self.payees = {}
        self.properties = {}
        self.operations = []

        if data is not None:
            self.load(data)

    def load(self, data):
        stuff = [
            (self.currencies, 'cur'),
            (self.accounts, 'account'),
            (self.categories, 'cat'),
            (self.payees, 'pay'),
            # (self.tags, 'tag'), not used
        ]

        for dict_, name in stuff:
            elements = getattr(data, name, [])

            for element in elements:
                key = element['key']
                dict_[key] = element._attributes

        operations = getattr(data, 'ope', [])

        for operation in operations:
            self.operations.append(operation._attributes)

        self.properties = getattr(data.properties, '_attributes', {})

        self._postprocess_accounts()
        self._postprocess_categories()
        self._postprocess_payees()
        self._postprocess_operations()

    def _get_category_type(self, category):
        flags = int(category.get('flags', 0))

        is_income = flags & self.INCOME_FLAG

        return config.INCOME_ACCOUNT if is_income else config.EXPENSE_ACCOUNT

    def _resolve_category_name(self, category):
        name = [category['_translated_name']]

        while 'parent' in category:
            category = self.categories[category['parent']]
            name.append(category['_translated_name'])

        return tuple(reversed(name))

    def _include_category(self, category):
        while not category['include'] and 'parent' in category:
            category['include'] = True
            category = self.categories[category['parent']]

        category['include'] = True

    def _postprocess_categories(self):
        for category in self.categories.values():
            category['_name'] = category['name']
            category['_translated_name'] = (
                self._translate_category(category['name']))

        for key, category in self.categories.items():
            category['name'] = self._resolve_category_name(category)
            category['type'] = self._get_category_type(category)

            category['unique_id'] = self._make_unique_id('category', key)
            category['include'] = False

    def _postprocess_accounts(self):
        for key, account in self.accounts.items():
            name = account['name']
            account['_name'] = name
            account['_str_name'] = self._translate_account(name)
            account['name'] = (account['_str_name'],)
            account['type'] = config.ASSETS_ACCOUNT
            account['initial'] = self._parse_float(account['initial'])
            account['currency'] = self.currencies[account['curr']]['iso']

            account['unique_id'] = self._make_unique_id('account', key)
            account['include'] = True

    def _postprocess_payees(self):
        for payee in self.payees.values():
            payee['_name'] = payee['name']
            payee['name'] = self._translate_payee(payee['name'])

    def _postprocess_operations(self):
        for op in self.operations:
            op['date'] = self._parse_date(op['date'])
            op['amount'] = self._parse_float(op['amount'])

            account = self.accounts[op['account']]
            op['account'] = account['unique_id']

            ignore_category = False

            if 'dst_account' in op:
                dst_account = self.accounts[op['dst_account']]
                op['dst_account'] = dst_account['unique_id']
                ignore_category = True

            op['currency'] = self.currencies[account['curr']]['iso']

            if 'payee' in op:
                payee = self.payees[op['payee']]['name']
                op['payee'] = payee

            if 'category' in op and not ignore_category:
                category = self.categories[op['category']]
                op['category'] = category['unique_id']
                self._include_category(category)

            if 'tags' in op:
                tags = self._split_tags(op['tags'])
                self._register_tags(tags)
                op['tags'] = [self.tags[tag] for tag in tags]

    def _register_tags(self, tags):
        for tag in tags:
            self.tags[tag] = self._translate_tag(tag)

    def _make_unique_id(self, kind, key):
        return f'{kind}_{key}'

    def _split_tags(self, tags):
        return self.TAG_SEP_REGEX.split(tags)

    def _parse_float(self, value):
        value = float(value)
        return Decimal(f'{value:.2f}')

    def _parse_date(self, value):
        return datetime.date(1, 1, 1) + datetime.timedelta(days=int(value) - 1)

    def _translate_account(self, name):
        return config.ACCOUNTS_DICT.get(name, name)

    def _translate_category(self, name):
        return config.CATEGORIES_DICT.get(name, name)

    def _translate_tag(self, name):
        return config.TAGS_DICT.get(name, name)

    def _translate_payee(self, name):
        return config.PAYEE_DICT.get(name, name)


class Beancount:
    NAME_FORBIDDEN_CHARS_REGEX = re.compile(r"[?/&()' \[\]\\]")
    DASH_COLON_DASH_REGEX = re.compile(r'-*:-*')
    DASH_EOL_REGEX = re.compile(r'-+$')
    DASH_DASH_REGEX = re.compile(r'--+')

    def __init__(self):
        self.entries = []
        self.pad_balances = []
        self.transactions = []
        self.accounts = []
        self._lineno_counter = 0

        self.add_account(config.OPENING_BALANCE_ACCOUNT)

    def add_account(self, name, date=None, currency=None,
                    initial_amount=None):
        date = date or config.DEFAULT_DATE
        name = self._format_account_name(name)
        self.accounts.append(name)

        currencies = currency and [currency]

        self.entries.append(
            bc.Open(self._get_meta(), date, name, currencies, booking=None)
        )

        if initial_amount is not None and initial_amount != 0:
            assert currency is not None

            self.pad_balances.append(
                bc.Pad(self._get_meta(), date=config.DEFAULT_PAD_DATE,
                       account=name,
                       source_account=config.OPENING_BALANCE_ACCOUNT)
            )
            self.pad_balances.append(
                bc.Balance(self._get_meta(),
                           date=config.DEFAULT_BALANCE_DATE, account=name,
                           amount=bc.Amount(initial_amount, currency),
                           tolerance=None, diff_amount=None)
            )

        return len(self.accounts) - 1  # index of the account on self.accounts

    def add_transaction(self, date, payee, narration, main_account,
                        other_account, amount, currency, tags):
        posting_common_args = dict(cost=None, price=None, flag=None, meta=None)

        if config.PREFER_POSITIVE_AMOUNTS and amount < 0:
            main_account, other_account = other_account, main_account
            amount = -amount

        postings = [
            bc.Posting(main_account, bc.Amount(amount, currency),
                       **posting_common_args),
            bc.Posting(other_account, None,
                       **posting_common_args),
        ]

        self.transactions.append(
            bc.Transaction(self._get_meta(), date, flag=config.DEFAULT_FLAG,
                           payee=payee, narration=narration, tags=tags,
                           links=None, postings=postings)
        )

    def print(self, output):
        printer.print_entries(
            list(chain(
                self.entries,
                self.pad_balances,
                bc.sorted(self.transactions)
            )),
            file=output
        )

    def _get_meta(self):
        self._lineno_counter += 1
        return {'lineno': self._lineno_counter}

    def _format_account_name(self, name):
        name = self.NAME_FORBIDDEN_CHARS_REGEX.sub('-', name)
        name = self.DASH_COLON_DASH_REGEX.sub(':', name)
        name = self.DASH_EOL_REGEX.sub('', name)
        name = self.DASH_DASH_REGEX.sub('-', name)
        name = unidecode(name)
        return config.BC_ACCOUNTS_DICT.get(name, name)


def convert(xml):
    xhb = Homebank(xml.homebank)

    beancount = Beancount()

    account_map = {}

    for item in chain(xhb.accounts.values(), xhb.categories.values()):
        if config.REMOVE_EMPTY_CATEGORIES and not item['include']:
            continue

        name = ':'.join((item['type'], *item['name']))

        id_ = beancount.add_account(
            name=name,
            currency=item.get('currency'),
            initial_amount=item.get('initial'),
        )

        account_map[item['unique_id']] = id_

    for op in xhb.operations:
        paymode = op.get('paymode')
        main_account = beancount.accounts[account_map[op['account']]]
        amount = op['amount']

        if paymode == Homebank.INTERNAL_TRANSFER:
            if amount < 0:
                continue  # only register the positive transfer

            other_account = beancount.accounts[account_map[op['dst_account']]]
        else:
            other_account = beancount.accounts[account_map[op['category']]]

        beancount.add_transaction(
            date=op['date'],
            payee=op.get('payee'),
            narration=op.get('info'),
            main_account=main_account,
            other_account=other_account,
            amount=amount,
            currency=op['currency'],
            tags=op.get('tags'),
        )

    return beancount


def print_dicts(xml, output=None):
    if output is None:
        output = sys.stdout

    homebank = Homebank(xml.homebank)

    def build_dict(iterable, key1='_name', key2='name', filter_=None):
        return {
            item[key1]: item[key2] for item in iterable
            if filter_ is None or filter_(item)
        }

    dicts = [
        ('CATEGORIES_DICT',
         build_dict(
             homebank.categories.values(),
             key2='_translated_name',
             filter_=lambda item: (item.get('include') or
                                   not config.REMOVE_EMPTY_CATEGORIES))),
        ('ACCOUNTS_DICT',
         build_dict(homebank.accounts.values(), key2='_str_name')),
        ('PAYEE_DICT',
         build_dict(homebank.payees.values())),
        ('TAGS_DICT', homebank.tags),
    ]

    for name, dict_ in dicts:
        print("{name} = \\\n{dict}".format(
            name=name,
            dict=pformat(dict_, indent=4),
        ), file=output)


def overwrite_config(new_config):
    global config

    for attribute in dir(new_config):
        if attribute.startswith('_'):
            continue

        if hasattr(config, attribute):
            value = getattr(new_config, attribute)
            setattr(config, attribute, value)
        else:
            msg = f"Unrecognized config attribute {attribute}."
            warnings.warn(msg)
