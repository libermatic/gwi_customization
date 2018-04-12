# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate


@frappe.whitelist()
def get_undisbursed_principal(loan):
    """Gets undisbursed principal"""
    principal, loan_account = frappe.get_value(
        'Microfinance Loan',
        loan,
        ['loan_principal', 'loan_account'],
    )
    if not principal or not loan_account:
        raise frappe.DoesNotExistError("Loan: {} not found".format(loan))
    conds = [
        "account = '{}'".format(loan_account),
        "voucher_type = 'Microfinance Disbursement'",
        "against_voucher_type = 'Microfinance Loan'",
        "against_voucher = '{}'".format(loan)
    ]
    disbursed = frappe.db.sql(
        """
            SELECT sum(debit)
            FROM `tabGL Entry`
            WHERE {}
        """.format(" AND ".join(conds))
    )[0][0] or 0
    return principal - disbursed


@frappe.whitelist()
def get_outstanding_principal(loan, posting_date=None):
    """Get outstanding principal"""
    loan_account = frappe.get_value('Microfinance Loan', loan, 'loan_account')
    cond = [
        "account = '{}'".format(loan_account),
        "against_voucher_type = 'Microfinance Loan'",
        "against_voucher = '{}'".format(loan),
    ]
    if posting_date:
        cond.append("posting_date <= '{}'".format(getdate(posting_date)))
    outstanding = frappe.db.sql(
        """
            SELECT sum(debit) - sum(credit)
            FROM `tabGL Entry`
            WHERE {}
        """.format(" AND ".join(cond))
    )[0][0] or 0
    return outstanding
