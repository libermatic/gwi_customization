# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


@frappe.whitelist()
def get_service_details(loanee=None, customer=None):
    if customer:
        Loanee = frappe.qb.DocType("Microfinance Loanee")
        q = (
            frappe.qb.from_(Loanee)
            .select(Loanee.date_of_retirement, Loanee.net_salary_amount)
            .where(Loanee.customer == customer)
            .limit(1)
        )
        results = q.run(as_dict=1)
        try:
            return results[0]
        except IndexError:
            return None
    if loanee:
        pass
    return None
