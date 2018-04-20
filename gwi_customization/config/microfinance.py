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
                {
                    "type": "doctype",
                    "name": "Microfinance Loanee",
                    "label": "Loanee",
                    "description": _("Loanee details"),
                },
            ]
        },
        {
            "label": _("Transactions"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Microfinance Disbursement",
                    "label": "Disbursement",
                    "description": _("Loan payout to customers"),
                },
                {
                    "type": "doctype",
                    "name": "Microfinance Recovery",
                    "label": "Recovery",
                    "description": _("Loan payments received from customers"),
                },
                {
                    "type": "doctype",
                    "name": "Microfinance Write Off",
                    "label": "Write Off",
                    "description": _("Write offs to loan outstanding amounts"),
                },
            ]
        },
        {
            "label": _("Reports"),
            "items": [
                {
                    "type": "report",
                    "is_query_report": True,
                    "name": "Microfinance Loan Summary",
                    "label": "Loan Summary",
                },
                {
                    "type": "report",
                    "is_query_report": True,
                    "name": "Microfinance Account Statement",
                    "label": "Account Statement",
                },
                {
                    "type": "report",
                    "is_query_report": True,
                    "name": "Microfinance Asset Health",
                    "label": "Asset Health",
                },
            ]
        },
        {
            "label": _("Setup"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Microfinance Loan Plan",
                    "label": "Loan Plan",
                    "description": _("Types of loans"),
                },
                {
                    "type": "doctype",
                    "name": "Microfinance Charge Type",
                    "label": "Loan Charge",
                    "description": _(
                        "Types of charges that could be applicable"
                    ),
                },
                {
                    "type": "doctype",
                    "name": "Microfinance Loan Settings",
                    "label": "Loan Settings",
                    "description": _("Global loan configuration"),
                },
            ]
        },
        {
            "label": _("Tools"),
            "items": []
        },
    ]
