# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from functools import reduce
import frappe
from frappe.utils import flt, getdate, fmt_money
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from toolz import concatv

from gwi_customization.microfinance.api.loan import get_undisbursed_principal
from gwi_customization.microfinance.api.interest import update_advance_interests


class MicrofinanceDisbursement(AccountsController):
    def validate(self):
        to_disburse = flt(self.amount) + flt(self.recovered_amount)
        if to_disburse > get_undisbursed_principal(self.loan):
            frappe.throw("Disbursed amount cannot exceed the sanctioned amount")
        loan_start_date = frappe.get_value(
            "Microfinance Loan", self.loan, "posting_date"
        )
        if getdate(self.posting_date) < loan_start_date:
            frappe.throw("Cannot disburse before loan start date")

    def before_save(self):
        self.total_disbursed = flt(self.amount) + flt(self.recovered_amount)
        self.total_charges = reduce(lambda a, x: a + x.charge_amount, self.charges, 0)
        account_dict = get_bank_cash_account(
            mode_of_payment=self.mode_of_payment or "Cash", company=self.company
        )
        self.payment_account = account_dict.get("account")

    def on_submit(self):
        self.make_gl_entries()
        update_advance_interests(self.loan, self.posting_date)
        self.update_loan_status()

    def on_cancel(self):
        self.make_gl_entries(cancel=1)
        self.update_loan_status()

    def get_gl_dict(self, args):
        gl_dict = frappe._dict(
            {"against_voucher_type": "Microfinance Loan", "against_voucher": self.loan}
        )
        gl_dict.update(args)
        return super(MicrofinanceDisbursement, self).get_gl_dict(gl_dict)

    def make_gl_entries(self, cancel=0, adv_adj=0):
        self.is_opening = "Yes" if self.is_opening else "No"
        gl_entries = self.add_loan_gl_entries()
        if self.is_opening == "Yes" and self.recovered_amount:
            gl_entries = self.add_opening_gl_entries(gl_entries)
        if self.charges:
            gl_entries = self.add_charges_gl_entries(gl_entries)
        make_gl_entries(gl_entries, cancel=cancel, adv_adj=adv_adj, merge_entries=False)
        self.reload()

    def add_loan_gl_entries(self, gle=[]):
        remarks = (
            "Opening for orginal {}".format(
                fmt_money(
                    self.total_disbursed,
                    precision=0,
                    currency=frappe.defaults.get_user_default("currency"),
                )
            )
            if self.is_opening == "Yes"
            else "Loan disbursed"
        )
        return gle + [
            self.get_gl_dict({"account": self.loan_account, "debit": self.amount}),
            self.get_gl_dict(
                {
                    "account": self.payment_account,
                    "credit": self.amount,
                    "against": self.customer,
                    "remarks": remarks,
                }
            ),
        ]

    def add_opening_gl_entries(self, gle=[]):
        temp_account = "Temporary Opening - {}".format(
            frappe.db.get_value("Company", self.company, "abbr")
        )
        return concatv(
            gle,
            [
                self.get_gl_dict(
                    {
                        "account": self.loan_account,
                        "debit": self.recovered_amount,
                        "is_opening": "Yes",
                    }
                ),
                self.get_gl_dict(
                    {"account": temp_account, "credit": self.recovered_amount}
                ),
                self.get_gl_dict(
                    {
                        "account": self.loan_account,
                        "credit": self.recovered_amount,
                        "is_opening": "Yes",
                    }
                ),
                self.get_gl_dict(
                    {"account": temp_account, "debit": self.recovered_amount}
                ),
            ],
        )

    def add_charges_gl_entries(self, gle=[]):
        cost_center = frappe.db.get_value(
            "Microfinance Loan Settings", None, "cost_center"
        )
        return concatv(
            gle,
            map(
                lambda row: self.get_gl_dict(
                    {
                        "account": row.charge_account,
                        "credit": row.charge_amount,
                        "cost_center": cost_center,
                        "remarks": row.charge,
                    }
                ),
                self.charges,
            ),
            [
                self.get_gl_dict(
                    {
                        "account": self.payment_account,
                        "debit": self.total_charges,
                        "against": self.customer,
                        "remarks": "Payment received against service charges",
                    }
                )
            ],
        )

    def update_loan_status(self):
        """Method to update disbursement_status of Loan"""
        loan = frappe.get_doc("Microfinance Loan", self.loan)
        undisbursed_principal = get_undisbursed_principal(self.loan)
        current_status = loan.disbursement_status
        if loan.loan_principal > undisbursed_principal > 0:
            loan.disbursement_status = "Partially Disbursed"
        elif loan.loan_principal == undisbursed_principal:
            loan.disbursement_status = "Sanctioned"
        elif undisbursed_principal == 0:
            loan.disbursement_status = "Fully Disbursed"
        if loan.disbursement_status != current_status:
            loan.save()
