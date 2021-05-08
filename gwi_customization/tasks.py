# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import frappe
import operator
from functools import partial
from frappe.utils import today, getdate, get_first_day, get_last_day, add_months
from toolz import pluck

from gwi_customization.microfinance.api.interest import make_name
from gwi_customization.microfinance.utils.fp import pick, compose


def _get_active_loans_after(posting_date):
    return frappe.get_all(
        "Microfinance Loan",
        filters=[
            ["docstatus", "=", "1"],
            ["recovery_status", "in", "Not Started, In Progress"],
            ["billing_start_date", "<=", posting_date],
        ],
    )


def _interest_does_not_exists(d):
    return compose(
        operator.not_,
        partial(frappe.db.exists, "Microfinance Loan Interest"),
        partial(make_name, start_date=getdate(d)),
    )


def _create_interest_on(loan, posting_date, period_date=None):
    interest = frappe.new_doc("Microfinance Loan Interest")
    p_date = period_date if period_date else add_months(posting_date, -1)
    interest.update(
        {
            "loan": loan,
            "posting_date": posting_date,
            "period": getdate(p_date).strftime("%b %Y"),
            "start_date": get_first_day(p_date),
            "end_date": get_last_day(p_date),
        }
    )
    interest.insert()
    interest.submit()
    return interest


def generate_interest(posting_date):
    """
    Returns a list of new interests posted on posting_date.

    Processes all active loans which have an interest for the previous
    period as this one.
    """
    not_exists_filter = compose(
        _interest_does_not_exists, partial(add_months, months=-1)
    )
    get_loans = compose(
        partial(filter, not_exists_filter(posting_date)),
        partial(map, pick("name")),
        _get_active_loans_after,
    )
    for loan in get_loans(posting_date):
        _create_interest_on(loan, posting_date)


def _get_interests(end_date):
    return frappe.get_all(
        "Microfinance Loan Interest",
        filters=[
            ["docstatus", "=", "1"],
            ["status", "not in", "Clear, Fined"],
            ["end_date", "=", end_date],
        ],
    )


def _set_fine(docname):
    interest = frappe.get_doc("Microfinance Loan Interest", docname)
    interest.run_method("set_fine_amount")
    return interest


def generate_late_fines(posting_date):
    """
    Returns a list of interests that were posted in the previous period
    from the posting_date.

    Processes all interests in the previous period what have outstanding
    interest amounts.
    """
    get_interests = compose(
        partial(map, pick("name")),
        _get_interests,
        partial(add_months, months=-2),
        get_last_day,
    )
    for interest in get_interests(posting_date):
        _set_fine(interest)


def _submit_draft_interests(posting_date):
    interests = frappe.get_all(
        "Microfinance Loan Interest",
        filters={"posting_date": posting_date, "docstatus": 0},
    )
    for name in pluck("name", interests):
        doc = frappe.get_doc("Microfinance Loan Interest", name)
        doc.submit()


def monthly():
    posting_date = today()
    generate_late_fines(posting_date)
    _submit_draft_interests(posting_date)
    generate_interest(posting_date)
