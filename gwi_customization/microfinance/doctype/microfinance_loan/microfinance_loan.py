# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, get_last_day
from frappe.contacts.doctype.address.address import get_default_address
from gwi_customization.microfinance.utils.fp import join
from gwi_customization.microfinance.api.loan import get_chart_data


def _make_address_text(customer=None):
    """Returns formatted address of Customer"""
    if not customer:
        return None
    address = frappe.get_value(
        'Address',
        get_default_address('Customer', customer),
        ['address_line1', 'city'],
        as_dict=True
    )
    if not address:
        return None
    return join(', ')([address.get('address_line1'), address.get('city')])


class MicrofinanceLoan(Document):
    def onload(self):
        self.set_onload(
            'address_text', _make_address_text(self.customer)
        )
        if self.docstatus == 1:
            self.set_onload(
                'chart_data', get_chart_data(self.name)
            )

    def before_save(self):
        # set Loan Plan values
        rate_of_interest, rate_of_late_charges, calculation_slab = \
            frappe.get_value(
                'Microfinance Loan Plan',
                self.loan_plan,
                [
                    'rate_of_interest',
                    'rate_of_late_charges',
                    'calculation_slab',
                ]
            )
        if not self.rate_of_interest:
            self.rate_of_interest = rate_of_interest
        if not self.rate_of_late_charges:
            self.rate_of_late_charges = rate_of_late_charges
        if not self.calculation_slab:
            self.calculation_slab = calculation_slab

        # set Loan Settings values
        interest_income_account, loan_account = frappe.get_value(
            'Microfinance Loan Settings',
            None,
            ['interest_income_account', 'loan_account']
        )
        if not self.loan_account:
            self.loan_account = loan_account
        if not self.interest_income_account:
            self.interest_income_account = interest_income_account

    def before_submit(self):
        self.disbursement_status = 'Sanctioned'
        self.recovery_status = 'Not Started'
        # set to the first of the following month
        self.billing_start_date = add_days(get_last_day(self.posting_date), 1)
