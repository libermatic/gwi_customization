# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from gwi_customization.microfinance.doctype.microfinance_loan.\
    test_microfinance_loan import create_test_loan, remove_test_loan
from gwi_customization.microfinance.doctype.microfinance_disbursement.\
    test_microfinance_disbursement import (
        create_test_disbursement, remove_test_disbursement
    )
from gwi_customization.microfinance.utils import get_gle_by

get_write_off_gle = get_gle_by('Microfinance Write Off')


class TestMicrofinanceWriteOff(unittest.TestCase):
    def tearDown(self):
        remove_test_write_off()

    def test_gle(self):
        write_off = create_test_write_off(amount=15000)
        exp_gle = dict((d[0], d) for d in [
            ['Microfinance Loans - _TC', 0, 15000, None],
            ['Write Off - _TC', 15000, 0, None],
        ])
        gl_entries = get_write_off_gle(write_off.name)
        self.assertEqual(len(gl_entries), 2)
        for gle in gl_entries:
            self.assertEquals(exp_gle[gle.account][0], gle.account)
            self.assertEquals(exp_gle[gle.account][1], gle.debit)
            self.assertEquals(exp_gle[gle.account][2], gle.credit)
            self.assertEquals(exp_gle[gle.account][3], gle.against)
            self.assertEquals(write_off.loan, gle.against_voucher)

    def test_cancel_on_gle(self):
        write_off = create_test_write_off()
        write_off.cancel()
        gl_entries = get_write_off_gle(write_off.name)
        self.assertEqual(len(gl_entries), 0)


def create_test_write_off(**kwargs):
    args = frappe._dict(kwargs)
    if not args.skip_dependencies:
        create_test_loan(
            loan_no=args.loan or '_Test Loan 1',
            loan_principal=args.loan_principal or 100000.0,
            loan_plan=args.loan_plan or '_Test Loan Plan Eco'
        )
        create_test_disbursement(
            loan=args.loan or '_Test Loan 1',
            amount=args.loan_principal or 100000.0,
            skip_dependencies=True,
        )
    doc = frappe.new_doc('Microfinance Write Off')
    doc.update({
        'loan': args.loan or '_Test Loan 1',
        'posting_date': args.posting_date or '2017-09-17',
        'amount': args.amount or 25000.0,
        'reason': args.reason or '_Test Write Off Reason',
    })
    if not args.do_not_insert:
        doc.insert(ignore_if_duplicate=True)
        if not args.do_not_submit:
            doc.submit()
    return doc


def remove_test_write_off(loan='_Test Loan 1', keep_dependencies=False):
    write_offs = frappe.get_all(
        'Microfinance Write Off', filters=[['loan', 'in', loan]],
    )
    for doc in write_offs:
        try:
            rec = frappe.get_doc('Microfinance Write Off', doc.name)
            if rec.docstatus == 1:
                rec.cancel()
        except frappe.DoesNotExistError:
            pass
        frappe.delete_doc(
            doctype='Microfinance Write Off', name=doc.name, force=True
        )
    remove_test_disbursement(loan, keep_dependencies=keep_dependencies)
    if not keep_dependencies:
        remove_test_loan(loan)
