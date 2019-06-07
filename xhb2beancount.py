#!/usr/bin/env python3

import datetime
import sys

from beancount.core import data as bc
import untangle


DEFAULT_DATE = datetime.date(1970, 1, 1)


class Homebank:
    def __init__(self, xml):
        self.currencies = {}
        self.accounts = {}
        self.categories = {}
        self.tags = {}
        self.payees = {}
        self.properties = {}
        self.operations = []

        self.read_from_untangle(xml)

    def read_from_untangle(self, xml):
        stuff = [
            (self.currencies, 'cur'),
            (self.accounts, 'account'),
            (self.categories, 'cat'),
            (self.tags, 'tag'),
            (self.payees, 'pay'),
        ]

        for dict_, name in stuff:
            elements = getattr(xml, name, [])
            for element in elements:
                key = element['key']
                dict_[key] = element._attributes

        operations = getattr(xml, 'ope', [])
        for operation in operations:
            self.operations.append(operation._attributes)

        self.properties = getattr(xml.properties, '_attributes', {})
