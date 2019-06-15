#!/usr/bin/env python3

import datetime
import re
import sys
from decimal import Decimal
from itertools import chain

import untangle
from beancount.core import data as bc
from beancount.parser import printer
from text_unidecode import unidecode

from config import (ACCOUNT_SEP, ACCOUNTS_DICT, ASSETS_ACCOUNT,
                    CATEGORIES_DICT, DEFAULT_DATE, DEFAULT_FLAG,
                    EXPENSE_ACCOUNT, INCOME_ACCOUNT, INCOME_FLAG, PAYEE_DICT,
                    PREFER_POSITIVE_AMOUNTS, TAGS_DICT)


class Homebank:
    INTERNAL_TRANSFER = '5'
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
            (self.tags, 'tag'),
            (self.payees, 'pay'),
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
        self._postprocess_operations()

    def _get_category_type(self, category):
        flags = int(category.get('flags', 0))

        is_income = flags & INCOME_FLAG

        return INCOME_ACCOUNT if is_income else EXPENSE_ACCOUNT

    def _resolve_category_name(self, category):
        name = [category['name']]

        while 'parent' in category:
            category = self.categories[category['parent']]
            name.append(category['name'])

        return ACCOUNT_SEP.join(reversed(name))

    def _postprocess_categories(self):
        for key, category in self.categories.items():
            name = self._resolve_category_name(category)
            category['name'] = self._translate_category(name)
            category['type'] = self._get_category_type(category)

            category['unique_id'] = self._make_unique_id('category', key)

    def _postprocess_accounts(self):
        for key, account in self.accounts.items():
            name = account['name']
            account['name'] = self._translate_account(name)
            account['type'] = ASSETS_ACCOUNT
            account['initial'] = self._parse_float(account['initial'])
            account['currency'] = self.currencies[account['curr']]['iso']

            account['unique_id'] = self._make_unique_id('account', key)

    def _postprocess_operations(self):
        for op in self.operations:
            op['date'] = self._parse_date(op['date'])
            op['amount'] = self._parse_float(op['amount'])

            account = self.accounts[op['account']]
            if 'account' in op:
                op['account'] = account['unique_id']

            if 'dst_account' in op:
                dst_account = self.accounts[op['dst_account']]
                op['dst_account'] = dst_account['unique_id']

            op['currency'] = self.currencies[account['curr']]['iso']

            if 'payee' in op:
                payee = self._translate_payee(self.payees[op['payee']]['name'])
                op['payee'] = payee

            if 'category' in op:
                op['category'] = self.categories[op['category']]['unique_id']

            if 'tags' in op:
                op['tags'] = [self._translate_tag(tag)
                              for tag in self._split_tags(op['tags'])]

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
        return ACCOUNTS_DICT.get(name, name)

    def _translate_category(self, name):
        return CATEGORIES_DICT.get(name, name)

    def _translate_tag(self, name):
        return TAGS_DICT.get(name, name)

    def _translate_payee(self, name):
        return PAYEE_DICT.get(name, name)


class Beancount:
    NAME_FORBIDDEN_CHARS_REGEX = re.compile(r"[?/&()' \[\]\\]")
    DASH_COLON_DASH_REGEX = re.compile(r'-*:-*')
    DASH_EOL_REGEX = re.compile(r'-+$')

    def __init__(self):
        self.entries = []
        self.transactions = []
        self.accounts = []
        self._lineno_counter = 0

    def add_account(self, name, date=DEFAULT_DATE, currency=None,
                    initial_amount=None):
        name = self._format_account_name(name)
        self.accounts.append(name)

        currencies = currency and [currency]

        self.entries.append(
            bc.Open(self._get_meta(), date, name, currencies, booking=None)
        )

        return len(self.accounts) - 1  # index of the account on self.accounts

    def add_transaction(self, date, payee, narration, main_account,
                        other_account, amount, currency, tags):
        posting_common_args = dict(cost=None, price=None, flag=None, meta=None)

        if PREFER_POSITIVE_AMOUNTS and amount < 0:
            main_account, other_account = other_account, main_account
            amount = -amount

        postings = [
            bc.Posting(main_account, bc.Amount(amount, currency),
                       **posting_common_args),
            bc.Posting(other_account, None,
                       **posting_common_args),
        ]

        self.transactions.append(
            bc.Transaction(self._get_meta(), date, flag=DEFAULT_FLAG,
                           payee=payee, narration=narration, tags=tags,
                           links=None, postings=postings)
        )

    def print(self, output):
        printer.print_entries(
            list(chain(self.entries, bc.sorted(self.transactions))),
            file=output
        )

    def _get_meta(self):
        self._lineno_counter += 1
        return {'lineno': self._lineno_counter}

    def _format_account_name(self, name):
        name = self.NAME_FORBIDDEN_CHARS_REGEX.sub('-', name)
        name = self.DASH_COLON_DASH_REGEX.sub(':', name)
        name = self.DASH_EOL_REGEX.sub('', name)
        return unidecode(name)


def convert(xhb_filename):
    xml = untangle.parse(xhb_filename)
    xhb = Homebank(xml.homebank)

    beancount = Beancount()

    account_map = {}

    for item in chain(xhb.accounts.values(), xhb.categories.values()):
        name = ACCOUNT_SEP.join((item['type'], item['name']))

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
                continue  # only register the postive transfer

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


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} file.xhb', file=sys.stderr)
        exit(1)

    beancount = convert(sys.argv[1])
    beancount.print(sys.stdout)
