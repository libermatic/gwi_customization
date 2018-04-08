# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _


def get_data():
    return [
        {
            "label": _("Documents"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Microfinance Loan",
                    "label": "Loan",
                    "description": _("Customer loans"),
                },
            ]
        },
        {
            "label": _("Setup"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Customer",
                    "description": _("Customers"),
                },
                {
                    "type": "doctype",
                    "name": "Microfinance Loan Plan",
                    "label": "Loan Plan",
                    "description": _("Types of loans"),
                },
                {
                    "type": "doctype",
                    "name": "Microfinance Loan Settings",
                    "label": "Loan Settings",
                    "description": _("Global loan configuration"),
                },
            ]
        },
    ]
