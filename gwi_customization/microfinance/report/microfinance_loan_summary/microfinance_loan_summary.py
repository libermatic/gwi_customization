# Copyright (c) 2013, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
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
    return row + (
        sanctioned - undisbursed,
        recovered,
        outstanding,
    )


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

    conds = [
        "docstatus = 1",
    ]
    if filters.get('display') == 'Existing Loans':
        conds.append(
            "recovery_status in ('Not Started', 'In Progress')"
        )
    if filters.get('loan_plan'):
        conds.append(
            "loan_plan = '{}'".format(filters.get('loan_plan'))
        )
    result = frappe.db.sql(
        """
            SELECT posting_date, name, customer, loan_principal
            FROM `tabMicrofinance Loan`
            WHERE {}
        """.format(" AND ".join(conds))
    )
    data = map(_make_row, result)

    return columns, data
