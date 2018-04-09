# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

def update_doc(doc, salutation=None, customer_name=None, gender=None):
    if doc.salutation != salutation or doc.customer_name != customer_name \
            or doc.gender != gender:
        doc.update({
            'salutation': salutation,
            'customer_name': customer_name,
            'gender': gender,
        })
        doc.save()


class MicrofinanceLoanee(Document):
    def before_save(self):
        if not self.customer:
            try:
                customer = frappe.get_doc('Customer', {
                    'customer_name': self.customer_name
                })
            except frappe.DoesNotExistError:
                customer = frappe.get_doc({
                    'doctype': 'Customer',
                    'salutation': self.salutation,
                    'customer_name': self.customer_name,
                    'gender': self.gender,
                    'customer_type': 'Individual',
                    'customer_group': 'Individual',
                }).insert()
            self.customer = customer.name

    def on_update(self):
        customer = frappe.get_doc('Customer', self.customer)
        update_doc(
            customer,
            salutation=self.salutation,
            customer_name=self.customer_name,
            gender=self.gender,
        )


def on_customer_update(customer, event=None):
    try:
        loanee = frappe.get_doc(
            'Microfinance Loanee',
            {'customer': customer.name}
        )
        update_doc(
            loanee,
            salutation=customer.salutation,
            customer_name=customer.customer_name,
            gender=customer.gender,
        )
    except frappe.DoesNotExistError:
        pass
