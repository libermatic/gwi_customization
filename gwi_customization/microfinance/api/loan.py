# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import get_last_day, add_months, flt, rounded, cint
from functools import partial
from gwi_customization.microfinance.utils.fp import compose, pick
from gwi_customization.microfinance.utils import month_diff, calc_interest


def get_disbursed(loan):
    """Gets disbursed principal"""
    loan_account = frappe.get_value("Microfinance Loan", loan, "loan_account")
    if not loan_account:
        raise frappe.DoesNotExistError("Loan: {} not found".format(loan))

    GLEntry = frappe.qb.DocType("GL Entry")
    q = (
        frappe.qb.from_(GLEntry)
        .select(Sum(GLEntry.debit))
        .where(
            (GLEntry.account == loan_account)
            & (GLEntry.voucher_type == "Microfinance Disbursement")
            & (GLEntry.against_voucher_type == "Microfinance Loan")
            & (GLEntry.against_voucher == loan)
        )
    )
    return q.run()[0][0] or 0


@frappe.whitelist()
def get_undisbursed_principal(loan):
    """Gets undisbursed principal"""
    principal = frappe.get_value("Microfinance Loan", loan, "loan_principal")
    if not principal:
        raise frappe.DoesNotExistError("Loan: {} not found".format(loan))
    return principal - get_disbursed(loan)


def get_recovered_principal(loan):
    """Get recovered principal"""

    def get_sum_of(doctype, field):
        def fn(loan):
            return frappe.get_all(
                doctype, filters={"docstatus": 1, "loan": loan}, fields=field
            )

        return compose(sum, partial(map, pick(field)), fn)

    return get_sum_of("Microfinance Recovery", "principal_amount")(loan) + get_sum_of(
        "Microfinance Disbursement", "recovered_amount"
    )(loan)


@frappe.whitelist()
def get_outstanding_principal(loan, posting_date=None):
    """Get outstanding principal"""
    loan_account = frappe.get_value("Microfinance Loan", loan, "loan_account")

    GLEntry = frappe.qb.DocType("GL Entry")
    q = (
        frappe.qb.from_(GLEntry)
        .select(Sum(GLEntry.debit) - Sum(GLEntry.credit))
        .where(
            (GLEntry.account == loan_account)
            & (GLEntry.voucher_type == "Microfinance Loan")
            & (GLEntry.against_voucher == loan)
        )
    )

    if posting_date:
        q = q.where(GLEntry.posting_date < posting_date)
    return q.run()[0][0] or 0


def get_recovered(loan):
    loan_type = frappe.db.get_value("Microfinance Loan", loan, "loan_type")
    if loan_type != "EMI":
        return get_recovered_principal(loan)

    LoanInterest = frappe.qb.DocType("Microfinance Loan Interest")
    q = (
        frappe.qb.from_(LoanInterest)
        .where((LoanInterest.docstatus < 2) & (LoanInterest.loan == loan))
        .select(Sum(LoanInterest.paid_amount))
    )
    return q.run()[0][0] or 0


def get_unrecovered(loan):
    loan_type = frappe.db.get_value("Microfinance Loan", loan, "loan_type")
    if loan_type != "EMI":
        return get_outstanding_principal(loan)

    LoanInterest = frappe.qb.DocType("Microfinance Loan Interest")
    q = (
        frappe.qb.from_(LoanInterest)
        .where((LoanInterest.docstatus < 2) & (LoanInterest.loan == loan))
        .select(
            Sum(
                LoanInterest.billed_amount
                + LoanInterest.principal_amount
                + LoanInterest.fine_amount
                - LoanInterest.paid_amount
            )
        )
    )
    return q.run()[0][0] or 0


def get_chart_data(loan_name):
    recovered = get_recovered(loan_name)
    outstanding = get_unrecovered(loan_name)
    undisbursed = get_undisbursed_principal(loan_name)

    write_off_account = frappe.get_value(
        "Microfinance Loan Settings", None, "write_off_account"
    )

    GLEntry = frappe.qb.DocType("GL Entry")
    q = (
        frappe.qb.from_(GLEntry)
        .select(Sum(GLEntry.debit - GLEntry.credit))
        .where(
            (GLEntry.account == write_off_account)
            & (GLEntry.against_voucher == loan_name)
        )
    )
    wrote_off = q.run()[0][0] or 0

    data = {
        "labels": ["RC", "OS", "UD", "WO"],
        "datasets": [
            {
                "name": "Total",
                "values": [recovered, outstanding, undisbursed, wrote_off],
            }
        ],
    }
    return data


def update_recovery_status(loan_name, posting_date, status=None):
    """Method update recovery_status of Loan"""
    loan = frappe.get_doc("Microfinance Loan", loan_name)
    outstanding_principal = get_outstanding_principal(
        loan_name, posting_date=posting_date
    )
    current_status = loan.recovery_status
    current_clear = loan.clear_date
    if outstanding_principal == 0 and loan.disbursement_status == "Fully Disbursed":
        loan.clear_date = posting_date
        loan.recovery_status = "Repaid"
    else:
        loan.clear_date = None
        if status:
            loan.recovery_status = status
        elif outstanding_principal == loan.loan_principal:
            loan.recovery_status = "Not Started"
        else:
            loan.recovery_status = "In Progress"
    if loan.recovery_status != current_status or loan.clear_date != current_clear:
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
    plan = frappe.get_doc("Microfinance Loan Plan", loan_plan)
    if not plan.income_multiple or not plan.max_duration:
        frappe.throw("Missing values in Loan Plan")

    recovery_amount = flt(income) * plan.income_multiple / plan.max_duration

    duration = (
        plan.max_duration
        if plan.force_max_duration
        else min(
            plan.max_duration,
            compose(partial(month_diff, end_date), get_last_day)(execution_date),
        )
    )

    expected_eta = compose(partial(add_months, months=duration), get_last_day)(
        execution_date
    )

    principal = recovery_amount * duration
    initial_interest = calc_interest(
        principal, plan.rate_of_interest, plan.calculation_slab
    )

    return {
        "principal": rounded(principal, 2),
        "expected_eta": expected_eta,
        "duration": duration,
        "recovery_amount": rounded(recovery_amount, 2),
        "initial_interest": rounded(initial_interest, 2),
    }


@frappe.whitelist()
def update_amounts(name, principal_amount=None, recovery_amount=None):
    loan = frappe.get_doc("Microfinance Loan", name)
    if loan.docstatus != 1:
        frappe.throw("Can only execute on submitted loans")
    if cint(principal_amount) < get_disbursed(name):
        frappe.throw("Cannot set principal less than already disbursed amount")
    if principal_amount:
        loan.update({"loan_principal": principal_amount})
    if recovery_amount:
        loan.update({"recovery_amount": recovery_amount})
    loan.save()


@frappe.whitelist()
def set_npa(loan, npa_date, final_amount, remarks=None):
    loan_doc = frappe.get_doc("Microfinance Loan", loan)
    if not loan_doc:
        frappe.throw("Unable to find loan {}".format(loan))
    outstanding = get_outstanding_principal(loan, npa_date)
    wo_amount = outstanding - flt(final_amount)
    if wo_amount:
        write_off = frappe.get_doc(
            {
                "doctype": "Microfinance Write Off",
                "loan": loan,
                "posting_date": npa_date,
                "amount": wo_amount,
                "reason": remarks or "Negotiated to {}".format(final_amount),
                "write_off_type": "NPA",
            }
        )
        write_off.insert()
        write_off.submit()
    return wo_amount


def get_outstanding(loan, posting_date):
    LoanInterest = frappe.qb.DocType("Microfinance Loan Interest")
    q = (
        frappe.qb.from_(LoanInterest)
        .where(
            (LoanInterest.loan == loan) & (LoanInterest.posting_date <= posting_date)
        )
        .select(
            Sum(
                LoanInterest.billed_amount
                + LoanInterest.principal_amount
                + LoanInterest.fine_amount
                - LoanInterest.paid_amount
            )
        )
    )
    return q.run()[0][0] or 0
