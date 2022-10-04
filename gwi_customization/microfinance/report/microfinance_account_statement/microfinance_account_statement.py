# Copyright (c) 2013, Libermatic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from functools import reduce, partial
from gwi_customization.microfinance.utils.fp import compose, join
from gwi_customization.microfinance.api.loan import get_outstanding_principal


def _accum_reducer(acc, row):
    return acc + [row[:-1] + (acc[-1][5] + row[4],) + row[-1:]]


def _col_sum(idx):
    def fn(rows):
        return reduce(lambda a, x: a + x[idx], rows, 0)

    return fn


def execute(filters={}):
    columns = [
        _("Posting Date") + ":Date:90",
        _("Account") + ":Link/Account:150",
        _("Credit") + ":Currency/currency:90",
        _("Debit") + ":Currency/currency:90",
        _("Amount") + ":Currency/currency:90",
        _("Cummulative") + ":Currency/currency:90",
        _("Remarks") + "::240",
    ]

    company, loan_account = frappe.get_value(
        "Microfinance Loan", filters.get("loan"), ["company", "loan_account"]
    )
    accounts_to_exclude = [
        loan_account,
        "Temporary Opening - {}".format(
            frappe.db.get_value("Company", company, "abbr")
        ),
    ]
    GLEntry = frappe.qb.DocType("GL Entry")
    q = (
        frappe.qb.from_(GLEntry)
        .where(
            (GLEntry.against_voucher_type == "Microfinance Loan")
            & (GLEntry.against_voucher == filters.get("loan"))
            & (GLEntry.account.notin(accounts_to_exclude))
        )
    )

    opening_entries = (
        q.select(
            Sum(GLEntry.credit, "credit"),
            Sum(GLEntry.debit, "debit"),
            Sum(GLEntry.credit - GLEntry.debit, "amount"),
        ).where(GLEntry.posting_date < filters.get("from_date"))
    ).run(as_dict=True)[0]
    results = (
        q.select(
            GLEntry.posting_date,
            GLEntry.account,
            Sum(GLEntry.credit, "credit"),
            Sum(GLEntry.debit, "debit"),
            Sum(GLEntry.credit - GLEntry.debit, "amount"),
            GLEntry.remarks,
        )
        .where(GLEntry.posting_date[filters.get("from_date") : filters.get("to_date")])
        .groupby(
            GLEntry.posting_date, GLEntry.account, GLEntry.voucher_no, GLEntry.remarks
        )
        .orderby(GLEntry.posting_date, GLEntry.name)
    ).run()

    opening_credit = opening_entries.get("credit") or 0
    opening_debit = opening_entries.get("debit") or 0
    opening_amount = opening_entries.get("amount") or 0
    total_credit = _col_sum(2)(results)
    total_debit = _col_sum(3)(results)
    total_amount = _col_sum(4)(results)
    opening = (
        None,
        _("Opening"),
        opening_credit,
        opening_debit,
        opening_amount,
        opening_amount,
        None,
    )
    total = (None, _("Total"), total_credit, total_debit, total_amount, None, None)
    closing = (
        None,
        _("Closing"),
        opening_credit + total_credit,
        opening_debit + total_debit,
        opening_amount + total_amount,
        get_outstanding_principal(filters.get("loan"), filters.get("to_date")),
        None,
    )
    data = reduce(_accum_reducer, results, [opening]) + [total, closing]

    return columns, data
