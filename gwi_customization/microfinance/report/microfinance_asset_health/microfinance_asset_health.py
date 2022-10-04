# Copyright (c) 2013, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.query_builder.functions import Max
from frappe.utils import today, add_months, cint, getdate
from functools import partial
from operator import neg
from gwi_customization.microfinance.utils.fp import compose, join
from gwi_customization.microfinance.api.loan import get_outstanding_principal
from gwi_customization.microfinance.api.interest import get_current_interest


def _result_to_data(row):
    return row[:-1] + (
        get_outstanding_principal(row[1]),
        get_current_interest(row[1], today()),
    )


def _display_filter(display):
    npa_date = compose(
        getdate,
        partial(add_months, today()),
        neg,
        cint,
        partial(frappe.get_value, "Microfinance Loan Settings", None),
    )("npa_duration")

    def fn(row):
        loan_start_date = row[-1]
        last_recovery_date = row[3]
        recovery_status = row[2]
        if display == "NPA Only":
            date_to_check = (
                max(loan_start_date, last_recovery_date)
                if last_recovery_date
                else loan_start_date
            )
            return recovery_status != "Repaid" and date_to_check < npa_date
        if display == "Existing Loans":
            return recovery_status in ["Not Started", "In Progress"]
        return True

    return fn


def execute(filters=None):
    columns = [
        _("Customer") + ":Link/Customer:180",
        _("Loan No") + ":Link/Microfinance Loan:90",
        _("Status") + "::90",
        _("Last Payment Date") + ":Date:90",
        _("Last Paid Interest") + "::90",
        _("Outstanding") + ":Currency/currency:90",
        _("Curent Interest") + ":Currency/currency:90",
    ]

    Loan = frappe.qb.DocType("Microfinance Loan")
    Recovery = frappe.qb.DocType("Microfinance Recovery")
    LoanInterest = frappe.qb.DocType("Microfinance Loan Interest")
    q = (
        frappe.qb.from_(Loan)
        .left_join(Recovery)
        .on((Recovery.docstatus == 1) & (Recovery.loan == Loan.name))
        .left_join(LoanInterest)
        .on(
            (LoanInterest.docstatus == 1)
            & (LoanInterest.loan == Loan.name)
            & (LoanInterest.billed_amount == LoanInterest.paid_amount)
        )
        .select(
            Loan.customer,
            Loan.name,
            Loan.recovery_status,
            Max(Recovery.posting_date),
            LoanInterest.period,
            Loan.posting_date,
        )
        .where((Loan.docstatus == 1) & (Loan.disbursement_status != "Sanctioned"))
        .groupby(Loan.name)
    )

    for field in ["name", "customer", "loan_plan"]:
        if filters.get(field):
            q = q.where(Loan[field] == filters.get(field))
    result = q.run()
    data = compose(
        list,
        partial(map, _result_to_data),
        partial(filter, _display_filter(filters.get("display"))),
    )(result)
    return columns, data
