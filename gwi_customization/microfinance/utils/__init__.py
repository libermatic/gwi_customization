# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def get_gle_by(voucher_type):
    """
        Build a function that returns GL Entries of a particular voucher_type
    """
    def fn(voucher_no):
        return frappe.db.sql(
            """
                SELECT
                    account,
                    SUM(debit) AS debit,
                    SUM(credit) AS credit,
                    against,
                    against_voucher
                FROM `tabGL Entry`
                WHERE voucher_type='{type}' AND voucher_no='{no}'
                GROUP BY account
                ORDER BY account ASC
            """.format(type=voucher_type, no=voucher_no),
            as_dict=1
        )
    return fn
