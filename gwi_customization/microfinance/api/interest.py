# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, add_days, get_last_day, getdate
from gwi_customization.microfinance.api.loan import get_outstanding_principal
from gwi_customization.microfinance.utils import calc_interest


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
            'period_label': start_date.strftime('%b, %Y'),
            'start_date': start_date,
            'end_date': end_date,
            'billed_amount': interest_amount,
            'outstanding_amount': interest_amount,
        }
        start_date = add_days(end_date, 1)


@frappe.whitelist()
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


@frappe.whitelist()
def get_last_paid(loan):
    return frappe.db.sql(
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
        print(per)
        periods.append(per)
        to_allocate -= per.get('allocated_amount')
    return periods
