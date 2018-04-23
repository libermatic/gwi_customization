# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils \
    import flt, add_days, add_months, get_last_day, getdate, formatdate
from functools import partial
from gwi_customization.microfinance.api.loan import get_outstanding_principal
from gwi_customization.microfinance.utils import calc_interest
from gwi_customization.microfinance.utils.fp import update, join, compose


def _interest_to_period(interest):
    billed_amount = flt(interest.get('billed_amount'))
    paid_amount = flt(interest.get('paid_amount'))
    return {
        'period_label': interest.get('period'),
        'start_date': interest.get('start_date'),
        'end_date': interest.get('end_date'),
        'billed_amount': billed_amount,
        'outstanding_amount': billed_amount - paid_amount,
    }


def _allocate(period, amount):
    outstanding_amount = flt(period.get('outstanding_amount'))
    allocated_amount = outstanding_amount \
        if outstanding_amount < amount else amount
    period.update({
        'allocated_amount': allocated_amount
    })
    return period


def _generate_periods(init_date, interest_amount):
    start_date = getdate(init_date)
    while True:
        end_date = get_last_day(start_date)
        yield {
            'period_label': start_date.strftime('%b %Y'),
            'start_date': start_date,
            'end_date': end_date,
            'billed_amount': interest_amount,
            'outstanding_amount': interest_amount,
        }
        start_date = add_days(end_date, 1)


def get_unpaid(loan):
    return frappe.db.sql(
        """
            SELECT
                loan, posting_date, period, start_date, end_date,
                billed_amount, paid_amount
            FROM `tabMicrofinance Loan Interest`
            WHERE loan='{loan}' AND paid_amount < billed_amount
            ORDER BY start_date
        """.format(loan=loan),
        as_dict=True,
    )


def get_last_paid(loan):
    res = frappe.db.sql(
        """
            SELECT
                loan, posting_date, period, start_date, end_date,
                billed_amount, paid_amount
            FROM `tabMicrofinance Loan Interest`
            WHERE loan='{loan}' AND paid_amount = billed_amount
            ORDER BY start_date DESC
            LIMIT 1
        """.format(loan=loan),
        as_dict=True,
    )
    return res[0] if res else None


@frappe.whitelist()
def allocate_interests(loan, posting_date, amount_to_allocate):
    periods = []
    to_allocate = amount_to_allocate

    existing_unpaid_interests = get_unpaid(loan)
    for period in map(_interest_to_period, existing_unpaid_interests):
        p = _allocate(period, to_allocate)
        periods.append(p)
        to_allocate -= p.get('allocated_amount')

    calculation_slab, loan_date, rate_of_interest = frappe.get_value(
        'Microfinance Loan',
        loan,
        ['calculation_slab', 'posting_date', 'rate_of_interest'],
    )
    outstanding_amount = get_outstanding_principal(loan, posting_date)
    interest_amount = calc_interest(
        outstanding_amount, rate_of_interest, calculation_slab
    )
    last = get_last_paid(loan)
    init_date = add_days(periods[-1].get('end_date'), 1) if periods \
        else add_days(last.get('end_date'), 1) if last \
        else loan_date
    gen_per = _generate_periods(init_date, interest_amount)
    while to_allocate > 0:
        per = _allocate(gen_per.next(), to_allocate)
        periods.append(per)
        to_allocate -= per.get('allocated_amount')
    return periods


@frappe.whitelist()
def get_current_interest(loan, posting_date):
    outstanding = get_outstanding_principal(loan, posting_date)
    calculation_slab, rate_of_interest = frappe.get_value(
        'Microfinance Loan',
        loan,
        ['calculation_slab', 'rate_of_interest'],
    )
    return calc_interest(
        outstanding, rate_of_interest, calculation_slab
    )


def make_name(loan, start_date):
    return loan + '/' + formatdate(start_date, 'YYYY-MM')


def _make_list_item(row):
    outstanding_amount = row.billed_amount - row.paid_amount
    if outstanding_amount == row.billed_amount:
        status = 'Billed'
    elif outstanding_amount > 0:
        status = 'Pending'
    else:
        status = 'Complete'
    return update({
        'outstanding_amount': outstanding_amount,
        'status': status,
    })(row)


def _gen_dates(from_date, to_date):
    current_date = getdate(from_date)
    while current_date <= getdate(to_date):
        yield current_date
        current_date = add_months(current_date, 1)


@frappe.whitelist()
def list(loan, from_date, to_date):
    if getdate(to_date) < getdate(from_date):
        return frappe.throw('To date cannot be less than From date')

    conds = [
        "loan = '{}'".format(loan),
        "docstatus = 1",
        "start_date BETWEEN '{}' AND '{}'".format(from_date, to_date),
    ]
    existing = frappe.db.sql(
        """
            SELECT
                name,
                period, posting_date, start_date,
                billed_amount, paid_amount
            FROM `tabMicrofinance Loan Interest` WHERE {conds}
        """.format(
            conds=join(" AND ")(conds)
        ),
        as_dict=True,
    )
    existing_dict = dict((row.name, row) for row in existing)

    get_item = compose(existing_dict.get, partial(make_name, loan))
    make_item = compose(_make_list_item, get_item)
    loan_date = frappe.get_value('Microfinance Loan', loan, 'posting_date')

    def make_empty(d):
        return {
            'name': make_name(loan, d),
            'period': d.strftime('%b %Y'),
            'start_date': max(loan_date, d),
            'status': 'Unbilled'
        }

    dates = compose(
        partial(_gen_dates, to_date=to_date), partial(max, loan_date), getdate,
    )(from_date)

    return map(
        lambda x: make_item(x) if get_item(x) else make_empty(x), dates
    )
