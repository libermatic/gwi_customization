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


def update_recovery_status(loan_name, posting_date):
    """Method update recovery_status of Loan"""
    loan = frappe.get_doc('Microfinance Loan', loan_name)
    outstanding_principal = get_outstanding_principal(
        loan_name, posting_date=posting_date
    )
    current_status = loan.recovery_status
    current_clear = loan.clear_date
    if outstanding_principal == 0 \
            and loan.disbursement_status == 'Fully Disbursed':
        loan.clear_date = posting_date
        loan.recovery_status = 'Repaid'
    else:
        loan.clear_date = None
        if outstanding_principal == loan.loan_principal:
            loan.recovery_status = 'Not Started'
        else:
            loan.recovery_status = 'In Progress'
    if loan.recovery_status != current_status \
            or loan.clear_date != current_clear:
        return loan.save()
