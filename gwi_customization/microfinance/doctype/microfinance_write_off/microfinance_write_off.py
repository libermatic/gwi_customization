# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries
from gwi_customization.microfinance.api.loan import (
    update_recovery_status,
    get_outstanding_principal,
)


class MicrofinanceWriteOff(AccountsController):
    def on_save(self):
        self.current_outstanding = get_outstanding_principal(
            self.loan, self.posting_date
        )
        self.next_outstanding = self.current_outstanding - self.amount

    def on_submit(self):
        self.make_gl_entries()
        update_recovery_status(
            self.loan,
            self.posting_date,
            status="NPA" if self.write_off_type == "NPA" else None,
        )

    def on_cancel(self):
        self.ignore_linked_doctypes = ('GL Entry',)
        self.make_gl_entries(cancel=1)
        update_recovery_status(self.loan, self.posting_date)

    def get_gl_dict(self, args):
        gl_dict = frappe._dict(
            {"against_voucher_type": "Microfinance Loan", "against_voucher": self.loan}
        )
        gl_dict.update(args)
        return super(MicrofinanceWriteOff, self).get_gl_dict(gl_dict)

    def make_gl_entries(self, cancel=0, adv_adj=0):
        cost_center, write_off_account = frappe.db.get_value(
            "Microfinance Loan Settings", None, ["cost_center", "write_off_account"]
        )
        gl_entries = [
            self.get_gl_dict({"account": self.loan_account, "credit": self.amount}),
            self.get_gl_dict(
                {
                    "account": write_off_account,
                    "debit": self.amount,
                    "cost_center": cost_center,
                    "remarks": self.reason,
                }
            ),
        ]
        make_gl_entries(gl_entries, cancel=cancel, adv_adj=adv_adj, merge_entries=False)
