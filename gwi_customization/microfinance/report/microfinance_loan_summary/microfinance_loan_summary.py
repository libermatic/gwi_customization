# Copyright (c) 2013, Libermatic and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from gwi_customization.microfinance.api.loan import (
    get_undisbursed_principal,
    get_outstanding_principal,
    get_recovered_principal,
)


def _make_row(row):
    loan, sanctioned = row[1], row[3]
    undisbursed = get_undisbursed_principal(loan)
    outstanding = get_outstanding_principal(loan)
    recovered = get_recovered_principal(loan)
    return row + (sanctioned - undisbursed, recovered, outstanding)


def execute(filters={}):
    columns = [
        _("Posting Date") + ":Date:90",
        _("Loan ID") + ":Link/Microfinance Loan:90",
        _("Customer") + ":Link/Customer:120",
        _("Sanctioned Amount") + ":Currency/currency:90",
        _("Disbursed Amount") + ":Currency/currency:90",
        _("Recovered Amount") + ":Currency/currency:90",
        _("Outstanding Amount") + ":Currency/currency:90",
    ]

    Loan = frappe.qb.DocType("Microfinance Loan")
    q = (
        frappe.qb.from_(Loan)
        .select(Loan.posting_date, Loan.name, Loan.customer, Loan.loan_principal)
        .where(Loan.docstatus == 1)
    )
    if filters.get("display") == "Existing Loans":
        q = q.where(Loan.recovery_status.isin(["Not Started", "In Progress"]))
    if filters.get("loan_plan"):
        q = q.where(Loan.loan_plan == filters.get("loan_plan"))
    result = q.run()
    data = map(_make_row, result)

    return columns, list(data)
