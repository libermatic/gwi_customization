# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from operator import itemgetter

from gwi_customization.microfinance.doctype.microfinance_loan \
    .microfinance_loan import _make_address_text


def execute():
    loans = map(itemgetter('name'), frappe.get_all('Microfinance Loan'))
    for name in loans:
        address_text, customer = frappe.db.get_value(
            'Microfinance Loan', name, ['address_text', 'customer'],
        )
        customer_address = _make_address_text(customer)
        if not address_text and customer_address:
            frappe.db.set_value(
                'Microfinance Loan',
                name,
                'address_text',
                customer_address
            )
