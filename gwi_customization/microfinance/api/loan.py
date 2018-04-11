# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


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
