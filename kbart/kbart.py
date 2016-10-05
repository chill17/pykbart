#!/usr/bin/env python
# coding: utf-8

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from collections import OrderedDict
import datetime
import re

import six

from kbart.constants import (RP1_FIELDS, RP2_FIELDS, PROVIDER_FIELDS,
                             EMBARGO_CODES_TO_STRINGS)
from kbart.exceptions import (InvalidRP, ProviderNotFound,
                              UnknownEmbargoFormat, IncompleteDateInformation)


@six.python_2_unicode_compatible
class Kbart:
    """Kbart representation without having to remember field positions."""

    def __init__(self,
                 data=None,
                 provider=None,
                 rp=2,
                 fields=None):
        """
        Take or figure out the field names and zip them with values.

        Expected use is reading from a csv, but can build up the fields
        based on input.

        Args:
            data: Values for kbart fields, usually from csv
            provider: String of a publisher/provider's name. Kbart recommended
                practice allows publishers to define their own special fields
                to be tacked at the end. Some providers fields are provided. If
                not, just attach them to or pass them as 'fields'
            rp: Int of Recommended Practice version. Most organizations should
                be using RP2, but some early adopters, i.e. OCLC, still use
                RP1.
            fields: Iterable of field names to be attached to data.
                Will usually be passed from KbartReader class.
        """
        self.provider = provider
        self.rp = rp
        if data:
            self.data = data
        else:
            self.data = []

        if fields:
            self.fields = fields
        else:
            self.fields = self._create_fields()

        self._kbart_data = OrderedDict(six.moves.zip_longest(self.fields,
                                                             self.data,
                                                             fillvalue=''))

    def __getitem__(self, key):
        return self._kbart_data[key]

    def __setitem__(self, key, value):
        self._kbart_data[key] = value

    def __repr__(self):
        return ("{0}(data={1}, provider={2}, rp={3}, fields={4})\n"
                .format(self.__class__.__name__,
                        self.data,
                        self.provider,
                        self.rp,
                        self.fields))

    def __str__(self):
        output = [" -------\n"]
        output.extend([_format_strings(the_string=self._kbart_data[key],
                                       prefix="{0}: ".format(key),
                                       suffix="\n")
                      for key in self._kbart_data])
        return "".join(output)

    def __len__(self):
        return len(self._kbart_data)

    def get_fields(self, *args):
        """Get values for the listed keys."""
        if not args:
            return self._kbart_data.values()

        return [self._kbart_data[x] for x in args
                if x in self._kbart_data]

    @property
    def holdings(self):
        return list(self._kbart_data.values())[3:9]

    def serial_holdings_pp(self):
        return Holdings.pretty_print(self.holdings)

    @property
    def title(self):
        return self._kbart_data['publication_title']

    @title.setter
    def title(self, value):
        self._kbart_data['publication_title'] = value

    @property
    def embargo(self):
        return self._kbart_data['embargo_info']

    def embargo_pp(self):
        return Embargo.pretty_print(self.embargo)

    @property
    def print_id(self):
        return self._kbart_data['print_identifier']

    @print_id.setter
    def print_id(self, value):
        self._kbart_data['print_identifier'] = value

    @property
    def e_id(self):
        return self._kbart_data['online_identifier']

    @e_id.setter
    def e_id(self, value):
        self._kbart_data['online_identifier'] = value

    @property
    def publisher(self):
        return self._kbart_data['publisher_name']

    @publisher.setter
    def publisher(self, value):
        self._kbart_data['publisher_name'] = value

    def _create_fields(self):
        fields = list(RP1_FIELDS)
        if int(self.rp) == 2:
            fields.extend(RP2_FIELDS)
        elif not int(self.rp) == 1:
            raise InvalidRP

        if self.provider is not None:
            try:
                fields.extend(PROVIDER_FIELDS[self.provider])
            except KeyError:
                raise ProviderNotFound

        return fields


class Holdings:
    @staticmethod
    def pretty_print(holdings):
        if any(holdings):
            first, last = holdings[:3], holdings[3:]
            first_holding = Holdings._create_holdings_string(first)
            last_holding = Holdings._create_holdings_string(last)
            if not last_holding:
                last_holding = 'present'
            return '{0} - {1}'.format(first_holding, last_holding)
        else:
            return 'No holdings present'

    @staticmethod
    def length_of_coverage(holdings):
        """
        If we have 2 dates, use them to determine length. Else assume holdings
        are 'to present', formulate a date and use that. If that doesn't work
        throw an exception that should be caught within the program.

        Returns:
            An int expressing how many years of coverage for that title

        Exceptions:
            IncompleteDateInformation: if no range can be produced
        """
        first_year, last_year = holdings[0], holdings[3]
        try:
            coverage_length = int(last_year) - int(first_year)
        except ValueError:
            try:
                this_year = datetime.datetime.now().year
                coverage_length = int(this_year) - int(first_year)
            except ValueError:
                raise IncompleteDateInformation

        return coverage_length

    @staticmethod
    def _create_holdings_string(holdings):
        """
        Format a section of KBART holdings into a human-readable string.
        Args:
            holdings: 3 element list; [date, vol, issue] following KBART order

        Returns:
            Human readable string of the holding period

        """
        holdings[1] = _format_strings(holdings[1], prefix='Vol: ')
        holdings[2] = _format_strings(holdings[2], prefix='Issue: ')
        return ', '.join([x for x in holdings if x])


class Embargo:
    pattern = re.compile('(?P<type>R|P)(?P<length>\d+)(?P<unit>D|M|Y)')

    @staticmethod
    def pretty_print(embargo):
        embargo_parts = Embargo._embargo_as_dict(embargo)
        try:
            type_of_embargo = EMBARGO_CODES_TO_STRINGS[embargo_parts['type']]
            length = embargo_parts['length']
            units = EMBARGO_CODES_TO_STRINGS[embargo_parts['unit']]
            return type_of_embargo.format(length, units)
        except KeyError as e:
            return ''

    @staticmethod
    def _embargo_as_dict(embargo):
        if embargo:
            try:
                embargo_parts = Embargo.pattern.match(embargo)
                embargo_dict = embargo_parts.groupdict()
            except AttributeError:
                raise UnknownEmbargoFormat
        else:
            embargo_dict = {}
        return embargo_dict


def _format_strings(the_string='', prefix='', suffix=''):
    if the_string:
        return '{0}{1}{2}'.format(prefix, the_string, suffix)
    else:
        return ''
