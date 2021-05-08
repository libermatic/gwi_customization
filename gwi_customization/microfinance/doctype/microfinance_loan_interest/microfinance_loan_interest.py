# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import add_months, flt
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from gwi_customization.microfinance.api.loan import (
    get_outstanding_principal,
    get_outstanding,
)
from gwi_customization.microfinance.api.interest import make_name
from gwi_customization.microfinance.utils import calc_interest


class MicrofinanceLoanInterest(AccountsController):
    def autoname(self):
        self.name = make_name(self.loan, self.start_date)

    def validate(self):
        self.validate_loan_status()
        self.validate_last_interest()

    def validate_loan_status(self):
        if "NPA" == frappe.db.get_value(
            "Microfinance Loan", self.loan, "recovery_status"
        ):
            frappe.throw("Cannot create or update interest for NPA loans")

    def validate_last_interest(self):
        loan_type, end_date = frappe.db.get_value(
            "Microfinance Loan", self.loan, ["loan_type", "billing_end_date"]
        )
        if (
            loan_type == "EMI"
            and end_date
            and frappe.utils.getdate(self.end_date) > end_date
        ):
            frappe.throw(
                "Cannot create interest for period after Loan End Date: {}".format(
                    end_date
                )
            )

    def before_save(self):
        if not self.billed_amount:
            self.billed_amount = self.get_billed_amount()

    def before_submit(self):
        self.status = self.get_status()

    def on_submit(self):
        self.make_gl_entries(
            self.billed_amount, remarks="Interest for {}".format(self.period)
        )

    def before_update_after_submit(self):
        self.validate_loan_status()
        before = self.get_doc_before_save()
        if self.billed_amount != before.billed_amount:
            if before.fine_amount:
                frappe.throw("Period already has been fined")
            self.status = self.get_status()
        if self.paid_amount != before.paid_amount:
            self.status = self.get_status()
        if self.fine_amount != before.fine_amount:
            if self.paid_amount == self.billed_amount:
                frappe.throw("No unpaid interest to make late charges for")
            if before.fine_amount:
                frappe.throw("Period has already been fined")
            if self.fine_amount > 0:
                self.status = "Fined"

    def before_cancel(self):
        self.validate_loan_status()

    def update_billed_amount(self, amount):
        self.billed_amount = amount
        self.save()

        interest_income_account = frappe.get_value(
            "Microfinance Loan", self.loan, "interest_income_account"
        )
        cur_billed = frappe.db.sql(
            """
                SELECT SUM(credit - debit)
                FROM `tabGL Entry`
                WHERE account = '{account}' AND voucher_no = '{voucher_no}'
            """.format(
                account=interest_income_account, voucher_no=self.name
            )
        )[0][0]
        if cur_billed != self.billed_amount:
            frappe.db.sql(
                """
                    DELETE FROM `tabGL Entry`
                    WHERE voucher_type={} AND voucher_no={}
                """.format(
                    self.doctype, self.name
                )
            )
            self.make_gl_entries(
                self.billed_amount, remarks="Interest for {}".format(self.period)
            )

    def adjust_billed_amount(self, posting_date):
        prev_billed = self.billed_amount
        self.billed_amount = self.get_billed_amount()
        if prev_billed != self.billed_amount:
            self.save()
            self.make_gl_entries(
                self.billed_amount - prev_billed,
                posting_date=posting_date,
                remarks="Adjustment to Interest for {}".format(self.period),
            )

    def get_billed_amount(self):
        (
            loan_type,
            calculation_slab,
            rate_of_interest,
            loan_principal,
        ) = frappe.get_value(
            "Microfinance Loan",
            self.loan,
            ["loan_type", "calculation_slab", "rate_of_interest", "loan_principal"],
        )
        if loan_type == "EMI":
            return calc_interest(loan_principal, rate_of_interest)
        outstanding_principal = get_outstanding_principal(self.loan, self.end_date)
        return calc_interest(outstanding_principal, rate_of_interest, calculation_slab)

    def set_fine_amount(self, amount=None):
        if amount:
            self.fine_amount = amount
        else:
            rate_of_late_charges, loan_type = frappe.get_value(
                "Microfinance Loan", self.loan, ["rate_of_late_charges", "loan_type"]
            )
            if loan_type == "EMI":
                outstanding = get_outstanding(self.loan, self.posting_date)
                self.fine_amount = outstanding * flt(rate_of_late_charges) / 100
            else:
                self.fine_amount = (
                    (self.billed_amount - flt(self.paid_amount))
                    * flt(rate_of_late_charges)
                    / 100
                )
        self.save()
        self.make_gl_entries(
            self.fine_amount,
            posting_date=add_months(self.end_date, 1),
            remarks="Late charge for {}".format(self.period),
        )

    def on_cancel(self):
        make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

    def get_gl_dict(self, args):
        gl_dict = frappe._dict(
            {"against_voucher_type": "Microfinance Loan", "against_voucher": self.loan}
        )
        gl_dict.update(args)
        return super(MicrofinanceLoanInterest, self).get_gl_dict(gl_dict)

    def make_gl_entries(self, amount, posting_date=None, remarks=""):
        self.company = frappe.get_value("Microfinance Loan", self.loan, "company")
        if posting_date:
            self.posting_date = posting_date
        interest_income_account, loan_account = frappe.db.get_value(
            "Microfinance Loan", self.loan, ["interest_income_account", "loan_account"]
        )
        cost_center = frappe.db.get_value(
            "Microfinance Loan Settings", None, "cost_center"
        )
        gl_entries = [
            self.get_gl_dict({"account": loan_account, "debit": amount}),
            self.get_gl_dict(
                {
                    "account": interest_income_account,
                    "credit": amount,
                    "cost_center": cost_center,
                    "remarks": remarks,
                }
            ),
        ]
        make_gl_entries(gl_entries, merge_entries=False)

    def get_status(self):
        if not self.paid_amount:
            return "Billed"
        if self.paid_amount < self.billed_amount:
            return "Pending"
        if self.paid_amount >= self.billed_amount:
            return "Clear"
