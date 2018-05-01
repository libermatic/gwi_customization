# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, get_last_day, add_months, flt, rounded
from functools import partial
from gwi_customization.microfinance.utils.fp import join, compose
from gwi_customization.microfinance.utils import month_diff, calc_interest


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


def get_recovered_principal(loan):
    """Get recovered principal"""
    loan_account = frappe.get_value('Microfinance Loan', loan, 'loan_account')
    conds = [
        "account = '{}'".format(loan_account),
        "against_voucher_type = 'Microfinance Loan'",
        "against_voucher = '{}'".format(loan),
    ]
    recovered = frappe.db.sql(
        """
            SELECT sum(credit) - sum(debit) FROM `tabGL Entry`
            WHERE voucher_type = 'Microfinance Recovery' AND {conds}
        """.format(
            conds=join(" AND ")(conds)
        )
    )[0][0] or 0
    unrecorded = frappe.db.sql(
        """
            SELECT sum(credit) FROM `tabGL Entry`
            WHERE voucher_type = 'Microfinance Disbursement' AND {conds}
        """.format(
            conds=join(" AND ")(conds)
        )
    )[0][0] or 0
    return recovered + unrecorded


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


def get_chart_data(loan_name):
    recovered = get_recovered_principal(loan_name)
    outstanding = get_outstanding_principal(loan_name)
    undisbursed = get_undisbursed_principal(loan_name)

    write_off_account = frappe.get_value(
        'Microfinance Loan Settings', None, 'write_off_account'
    )
    conds = [
        "account = '{}'".format(write_off_account),
        "against_voucher = '{}'".format(loan_name),
    ]
    wrote_off = frappe.db.sql(
        """
            SELECT SUM(debit - credit) FROM `tabGL Entry` WHERE {conds}
        """.format(
            conds=join(" AND ")(conds)
        )
    )[0][0] or 0

    data = {
        'labels': [
            'Recovered', 'Outstanding', 'Undisbursed', 'Wrote Off'
        ],
        'datasets': [
            {
                'title': "Total",
                'values': [recovered, outstanding, undisbursed, wrote_off]
            },
        ]
    }
    return data


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


@frappe.whitelist()
def calculate_principal(income, loan_plan, end_date, execution_date):
    """
        Return a dict containing the maximum allowed principal along with the
        duration and monthly installment.

        :param income: Renumeration received by the Customer
        :param loan_plan: Name of a Loan Plan
        :param end_date: Maximum date on which the loan could end
        :param execution_date: Date on which the loan would start
    """
    plan = frappe.get_doc('Microfinance Loan Plan', loan_plan)
    if not plan.income_multiple or not plan.max_duration:
        frappe.throw('Missing values in Loan Plan', ValueError)

    recovery_amount = flt(income) * plan.income_multiple / plan.max_duration

    duration = plan.max_duration if plan.force_max_duration else min(
        plan.max_duration,
        compose(
            partial(month_diff, end_date), get_last_day
        )(execution_date),
    )

    expected_eta = compose(
        partial(add_months, months=duration), get_last_day
    )(execution_date)

    principal = recovery_amount * duration
    initial_interest = calc_interest(
        principal, plan.rate_of_interest, plan.calculation_slab
    )

    return {
        'principal': rounded(principal, 2),
        'expected_eta': expected_eta,
        'duration': duration,
        'recovery_amount': rounded(recovery_amount, 2),
        'initial_interest': rounded(initial_interest, 2),
    }
