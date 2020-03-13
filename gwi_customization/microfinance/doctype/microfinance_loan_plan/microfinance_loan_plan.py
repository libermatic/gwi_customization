# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class MicrofinanceLoanPlan(Document):
    def validate(self):
        if self.loan_type == "EMI" and frappe.utils.cint(self.emi_duration) <= 0:
            frappe.throw(frappe._("Duration cannot be less than or equal to zero."))
