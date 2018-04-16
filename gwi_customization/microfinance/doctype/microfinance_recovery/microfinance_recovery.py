# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from functools import reduce
import frappe
from frappe.utils import flt
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.doctype.sales_invoice.sales_invoice \
    import get_bank_cash_account
from gwi_customization.microfinance.api.loan import get_outstanding_principal
from gwi_customization.microfinance.api.interest import allocate_interests


class MicrofinanceRecovery(AccountsController):
    def before_save(self):
        self.total_interests = \
            flt(self.total_amount) - flt(self.principal_amount)
        self.total_charges = reduce(
            lambda a, x: a + x.charge_amount, self.charges, 0
        )
        account_dict = get_bank_cash_account(
            mode_of_payment=self.mode_of_payment or 'Cash',
            company=self.company,
        )
        self.payment_account = account_dict.get('account')
        self.periods = []
        for period in allocate_interests(
            self.loan, self.posting_date, self.total_interests
        ):
            self.append('periods', period)

    def before_submit(self):
        self.make_interests()

    def on_submit(self):
        self.make_gl_entries()
        self.update_loan_status()

    def before_cancel(self):
        self.make_interests(cancel=1)

    def on_cancel(self):
        self.make_gl_entries(cancel=1)
        self.update_loan_status()

    def get_gl_dict(self, args):
        gl_dict = frappe._dict({
            'against_voucher_type': 'Microfinance Loan',
            'against_voucher': self.loan,
        })
        gl_dict.update(args)
        return super(MicrofinanceRecovery, self).get_gl_dict(gl_dict)

    def make_gl_entries(self, cancel=0, adv_adj=0):
        gl_entries = self.add_loan_gl_entries()
        if self.periods:
            gl_entries = self.add_interest_gl_entries(gl_entries)
        if self.charges:
            gl_entries = self.add_charges_gl_entries(gl_entries)
        make_gl_entries(
            gl_entries, cancel=cancel, adv_adj=adv_adj, merge_entries=False
        )

    def add_loan_gl_entries(self, gle=[]):
        return gle + [
            self.get_gl_dict({
                'account': self.loan_account,
                'credit': self.principal_amount,
            }),
            self.get_gl_dict({
                'account': self.payment_account,
                'debit': self.principal_amount,
                'against': self.customer,
                'remarks': 'Capital received',
            })
        ]

    def add_interest_gl_entries(self, gle=[]):
        return gle + [
            self.get_gl_dict({
                'account': self.loan_account,
                'credit': self.total_interests,
            }),
            self.get_gl_dict({
                'account': self.payment_account,
                'debit': self.total_interests,
                'against': self.customer,
                'remarks': 'Interest received',
            })
        ]

    def add_charges_gl_entries(self, gle=[]):
        cost_center = frappe.db.get_value(
            'Microfinance Loan Settings', None, 'cost_center'
        )
        return gle + map(
            lambda row: self.get_gl_dict({
                'account': row.charge_account,
                'credit': row.charge_amount,
                'cost_center': cost_center,
                'remarks': row.charge,
            }),
            self.charges
        ) + [
            self.get_gl_dict({
                'account': self.payment_account,
                'debit': self.total_charges,
                'against': self.customer,
            })
        ]

    def make_interests(self, cancel=0):
        if cancel:
            for period in self.periods:
                frappe.delete_doc_if_exists(
                    'Microfinance Loan Interest', period.ref_interest
                )
        else:
            for period in self.periods:
                interest = frappe.get_doc({
                    'doctype': 'Microfinance Loan Interest',
                    'loan': self.loan,
                    'posting_date': self.posting_date,
                    'period': period.period_label,
                    'start_date': period.start_date,
                    'end_date': period.end_date,
                    'billed_amount': period.billed_amount,
                    'paid_amount': period.allocated_amount,
                }).insert(ignore_if_duplicate=True)
                period.update({'ref_interest': interest.name})

    def update_loan_status(self):
        """Method update recovery_status of Loan"""
        loan = frappe.get_doc('Microfinance Loan', self.loan)
        outstanding_principal = get_outstanding_principal(
            self.loan, posting_date=self.posting_date
        )
        current_status = loan.recovery_status
        current_clear = loan.clear_date
        if outstanding_principal == 0 \
                and loan.disbursement_status == 'Fully Disbursed':
            loan.clear_date = self.posting_date
            loan.recovery_status = 'Repaid'
        else:
            loan.clear_date = None
            if outstanding_principal == loan.loan_principal:
                loan.recovery_status = 'Not Started'
            else:
                loan.recovery_status = 'In Progress'
        if loan.recovery_status != current_status \
                or loan.clear_date != current_clear:
            return loan.save()
