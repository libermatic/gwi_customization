# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from functools import cmp_to_key
import frappe
from frappe.model.document import Document
from frappe.contacts.doctype.address.address import get_address_display


def update_doc(doc, salutation=None, customer_name=None, gender=None):
    if (
        doc.salutation != salutation
        or doc.customer_name != customer_name
        or doc.gender != gender
    ):
        doc.update(
            {"salutation": salutation, "customer_name": customer_name, "gender": gender}
        )
        doc.save()


class MicrofinanceLoanee(Document):
    def onload(self):
        filters = [
            ["Dynamic Link", "link_doctype", "=", "Customer"],
            ["Dynamic Link", "link_name", "=", self.customer],
            ["Dynamic Link", "parenttype", "=", "Address"],
        ]
        address_list = sorted(
            [
                a.update({"display": get_address_display(a)})
                for a in frappe.get_all("Address", filters=filters, fields=["*"])
            ],
            key=cmp_to_key(
                lambda a, b: (int(a.is_primary_address - b.is_primary_address))
                or (1 if a.modified - b.modified else 0)
            ),
            reverse=True,
        )
        self.set_onload("addr_list", address_list)

    def before_save(self):
        if not self.customer:
            customer_name = frappe.get_value(
                "Customer",
                filters={"customer_name": self.customer_name},
                fieldname="name",
            )
            if not customer_name:
                customer = frappe.get_doc(
                    {
                        "doctype": "Customer",
                        "salutation": self.salutation,
                        "customer_name": self.customer_name,
                        "gender": self.gender,
                        "customer_type": "Individual",
                        "customer_group": "Individual",
                    }
                ).insert()
                self.customer = customer.name
            else:
                self.customer = customer_name

    def on_update(self):
        customer = frappe.get_doc("Customer", self.customer)
        update_doc(
            customer,
            salutation=self.salutation,
            customer_name=self.customer_name,
            gender=self.gender,
        )


def on_customer_update(customer, event=None):
    loanee_name = frappe.get_value(
        "Microfinance Loanee", filters={"customer": customer.name}, fieldname="name"
    )
    if loanee_name:
        loanee = frappe.get_doc("Microfinance Loanee", loanee_name)
        update_doc(
            loanee,
            salutation=customer.salutation,
            customer_name=customer.customer_name,
            gender=customer.gender,
        )
