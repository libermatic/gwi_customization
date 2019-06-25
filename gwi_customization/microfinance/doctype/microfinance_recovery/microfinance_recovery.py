# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from functools import reduce, partial
import frappe
from frappe.utils import flt, add_days, getdate
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from gwi_customization.microfinance.api.loan import (
    update_recovery_status,
    get_outstanding_principal,
)
from toolz import concatv

from gwi_customization.microfinance.api.interest import (
    allocate_interests,
    make_name,
    update_advance_interests,
)
from gwi_customization.microfinance.utils.fp import compose, update, join, pick


def _create_or_update_interest(opts, update=0):
    name = opts.get("ref_interest") or make_name(
        opts.get("loan"), opts.get("start_date")
    )
    if update or frappe.db.exists("Microfinance Loan Interest", name):
        doc = frappe.get_doc("Microfinance Loan Interest", name)
        paid_amount = (
            doc.paid_amount - opts.get("paid_amount")
            if update
            else doc.paid_amount + opts.get("paid_amount")
        )
        doc.update({"paid_amount": paid_amount})
        doc.save()
    else:
        doc = frappe.new_doc("Microfinance Loan Interest")
        doc.update(opts)
        doc.insert()
        doc.submit()
    return name


_stringify_periods = compose(join(", "), partial(map, lambda x: x.period_label))


class MicrofinanceRecovery(AccountsController):
    def validate(self):
        if self.total_interests and "NPA" == frappe.db.get_value(
            "Microfinance Loan", self.loan, "recovery_status"
        ):
            frappe.throw("Cannot recover interests for NPA loans")

    def before_save(self):
        self.total_amount = flt(self.total_interests) + flt(self.principal_amount)
        self.total_charges = reduce(lambda a, x: a + x.charge_amount, self.charges, 0)
        self.total_received = self.total_amount + self.total_charges
        account_dict = get_bank_cash_account(
            mode_of_payment=self.mode_of_payment or "Cash", company=self.company
        )
        self.payment_account = account_dict.get("account")
        self.periods = []
        for period in allocate_interests(
            self.loan,
            self.posting_date,
            amount_to_allocate=self.total_interests,
            principal=self.principal_amount,
        ):
            self.append("periods", period)
        expected_outstanding = self.principal_amount + compose(
            sum,
            partial(map, pick("outstanding_amount")),
            partial(filter, lambda x: x.ref_interest is not None),
        )(self.periods)
        if expected_outstanding > get_outstanding_principal(self.loan):
            frappe.throw("Cannot receive more than the current outstanding")

    def before_submit(self):
        sum_allocated = compose(sum, partial(map, pick("allocated_amount")))
        # validation for quirk when total_interests field is cleared and
        # Submit button is still being rendered instead of being changed to
        # Save
        if self.total_interests != sum_allocated(self.periods):
            frappe.throw(
                "Interests and total allocated do not match. "
                "Please refresh the page or update the interest"
            )

    def on_submit(self):
        self.make_principal_and_charges_gl_entries()
        update_advance_interests(self.loan, self.posting_date)
        interest_names = self.make_interests()
        for idx, item in enumerate(self.periods):
            if not item.ref_interest:
                item.ref_interest = interest_names[idx]
        self.flags.ignore_validate_update_after_submit = True
        self.save()
        self.make_period_gl_entries()
        update_recovery_status(self.loan, self.posting_date)

    def on_cancel(self):
        self.make_period_gl_entries(cancel=1)
        self.make_interests(cancel=1)
        self.make_principal_and_charges_gl_entries(cancel=1)
        update_recovery_status(self.loan, self.posting_date)

    def get_gl_dict(self, args):
        gl_dict = frappe._dict(
            {"against_voucher_type": "Microfinance Loan", "against_voucher": self.loan}
        )
        gl_dict.update(args)
        return super(MicrofinanceRecovery, self).get_gl_dict(gl_dict)

    def make_principal_and_charges_gl_entries(self, cancel=0, adv_adj=0):
        gl_entries = []
        if self.principal_amount:
            gl_entries = self.add_loan_gl_entries(gl_entries)
        if self.charges:
            gl_entries = self.add_charges_gl_entries(gl_entries)
        make_gl_entries(gl_entries, cancel=cancel, adv_adj=adv_adj, merge_entries=False)

    def make_period_gl_entries(self, cancel=0, adv_adj=0):
        gl_entries = []
        if self.periods:
            gl_entries = self.add_interest_gl_entries(gl_entries)
        make_gl_entries(gl_entries, cancel=cancel, adv_adj=adv_adj, merge_entries=False)

    def add_loan_gl_entries(self, gle=[]):
        return concatv(
            gle,
            [
                self.get_gl_dict(
                    {"account": self.loan_account, "credit": self.principal_amount}
                ),
                self.get_gl_dict(
                    {
                        "account": self.payment_account,
                        "debit": self.principal_amount,
                        "against": self.customer,
                        "remarks": "Capital received",
                    }
                ),
            ],
        )

    def add_interest_gl_entries(self, gle=[]):
        return concatv(
            gle,
            [
                self.get_gl_dict(
                    {"account": self.loan_account, "credit": self.total_interests}
                ),
                self.get_gl_dict(
                    {
                        "account": self.payment_account,
                        "debit": self.total_interests,
                        "against": self.customer,
                        "remarks": "Interest received for {}".format(
                            _stringify_periods(self.periods)
                        ),
                    }
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

    def make_interests(self, cancel=0):
        make_posting_date = compose(
            partial(min, getdate(self.posting_date)),
            getdate,
            partial(add_days, days=1),
            pick("end_date"),
        )
        return compose(
            list,
            partial(map, partial(_create_or_update_interest, update=cancel)),
            partial(
                map,
                compose(
                    update({"loan": self.loan}),
                    lambda x: {
                        "posting_date": make_posting_date(x),
                        "period": x.period_label,
                        "start_date": x.start_date,
                        "end_date": x.end_date,
                        "billed_amount": x.billed_amount,
                        "paid_amount": x.allocated_amount,
                    },
                ),
            ),
        )(self.periods)
