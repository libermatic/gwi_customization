# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import frappe
import operator
from functools import partial
from frappe.utils \
    import today, getdate, get_first_day, get_last_day, add_months
from gwi_customization.microfinance.api.interest import make_name
from gwi_customization.microfinance.utils.fp import pick, compose


def _get_active_loans_after(posting_date):
    return frappe.get_all(
        'Microfinance Loan',
        filters=[
            ['docstatus', '=', '1'],
            ['recovery_status', 'in', 'Not Started, In Progress'],
            ['billing_start_date', '<=', posting_date]
        ],
    )


def _interest_does_not_exists(d):
    return compose(
        operator.not_,
        partial(frappe.db.exists, 'Microfinance Loan Interest'),
        partial(make_name, start_date=getdate(d)),
    )


def _create_interest_on(loan, posting_date, period_date=None):
    interest = frappe.new_doc('Microfinance Loan Interest')
    p_date = period_date if period_date else add_months(posting_date, -1)
    interest.update({
        'loan': loan,
        'posting_date': posting_date,
        'period': getdate(p_date).strftime('%b %Y'),
        'start_date': get_first_day(p_date),
        'end_date': get_last_day(p_date),
    })
    interest.insert()
    interest.submit()
    return interest


def generate_interest(posting_date):
    not_exists_filter = compose(
        _interest_does_not_exists,
        partial(add_months, months=-1)
    )
    get_loans = compose(
        partial(filter, not_exists_filter(posting_date)),
        partial(map, pick('name')),
        _get_active_loans_after,
    )
    return map(
        partial(_create_interest_on, posting_date=posting_date),
        get_loans(posting_date),
    )


def _get_interests(end_date):
    return frappe.get_all(
        'Microfinance Loan Interest',
        filters=[
            ['docstatus', '=', '1'],
            ['status', 'not in', 'Clear, Fined'],
            ['end_date', '=', end_date]
        ],
    )


def _set_fine(docname):
    interest = frappe.get_doc('Microfinance Loan Interest', docname)
    interest.run_method('set_fine_amount')
    return interest


def generate_late_fines(posting_date):
    get_interests = compose(
        partial(map, pick('name')),
        _get_interests,
        partial(add_months, months=-2),
        get_last_day,
    )
    return map(
        _set_fine,
        get_interests(posting_date),
    )


def monthly():
    posting_date = today()
    generate_late_fines(posting_date)
    generate_interest(posting_date)
