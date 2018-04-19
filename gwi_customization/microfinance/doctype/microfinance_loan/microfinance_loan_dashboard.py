# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from frappe import _


def get_data():
    return {
        'fieldname': 'loan',
        'transactions': [
            {
                'label': _('Payments'),
                'items': ['Microfinance Disbursement', 'Microfinance Recovery']
            },
            {
                'label': _('Transactions'),
                'items': ['Microfinance Write Off']
            },
        ]
    }
