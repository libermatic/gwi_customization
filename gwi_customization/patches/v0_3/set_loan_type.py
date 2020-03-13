# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from toolz import pluck


def execute():
    for doctype in ["Microfinance Loan Plan", "Microfinance Loan"]:
        for name in pluck(
            "name", frappe.get_all(doctype, filters={"loan_type": ("in", ["", None])}),
        ):
            frappe.db.set_value(doctype, name, "loan_type", "Standard")
