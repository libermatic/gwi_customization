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

get_interest_gle = get_gle_by('Microfinance Loan Interest')


class TestMicrofinanceLoanInterest(unittest.TestCase):
    def tearDown(self):
        remove_test_interest()

    def test_generated_fields(self):
        interest = create_test_interest()
        self.assertEqual(interest.name, '_Test Loan 1/2017-08')
        self.assertEqual(interest.billed_amount, 5000.0)

    def test_gle(self):
        interest = create_test_interest()
        exp_gle = dict((d[0], d) for d in [
            ['Microfinance Loans - _TC', 5000, 0, None],
            ['Interests on Loans - _TC', 0, 5000, None],
        ])
        gl_entries = get_interest_gle(interest.name)
        self.assertEqual(len(gl_entries), 2)
        for gle in gl_entries:
            self.assertEquals(exp_gle[gle.account][0], gle.account)
            self.assertEquals(exp_gle[gle.account][1], gle.debit)
            self.assertEquals(exp_gle[gle.account][2], gle.credit)
            self.assertEquals(exp_gle[gle.account][3], gle.against)
            self.assertEquals(interest.loan, gle.against_voucher)

    def test_update_on_gle(self):
        interest = create_test_interest()
        interest.billed_amount = 4000
        interest.save()
        exp_gle = dict((d[0], d) for d in [
            ['Microfinance Loans - _TC', 4000, 0, None],
            ['Interests on Loans - _TC', 0, 4000, None],
        ])
        gl_entries = get_interest_gle(interest.name)
        self.assertEqual(len(gl_entries), 2)
        for gle in gl_entries:
            self.assertEquals(exp_gle[gle.account][0], gle.account)
            self.assertEquals(exp_gle[gle.account][1], gle.debit)
            self.assertEquals(exp_gle[gle.account][2], gle.credit)
            self.assertEquals(exp_gle[gle.account][3], gle.against)
            self.assertEquals(interest.loan, gle.against_voucher)

    def test_cancel_on_gle(self):
        interest = create_test_interest()
        remove_test_interest()
        gl_entries = get_interest_gle(interest.name)
        self.assertEqual(len(gl_entries), 0)


def create_test_interest(**kwargs):
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
    doc = frappe.new_doc('Microfinance Loan Interest')
    doc.update({
        'loan': args.loan or '_Test Loan 1',
        'posting_date': args.posting_date or '2017-09-17',
        'start_date': args.start_date or '2017-08-19',
        'end_date': args.start_date or '2017-08-31',
    })
    if not args.do_not_insert:
        doc.insert(ignore_if_duplicate=True)
    return doc


def remove_test_interest(loan='_Test Loan 1', keep_dependencies=False):
    interests = frappe.get_all(
        'Microfinance Loan Interest', filters=[['loan', 'in', loan]],
    )
    for doc in interests:
        try:
            rec = frappe.get_doc('Microfinance Loan Interest', doc.name)
            if rec.docstatus == 1:
                rec.cancel()
        except frappe.DoesNotExistError:
            pass
        frappe.delete_doc(
            doctype='Microfinance Loan Interest', name=doc.name, force=True
        )
    remove_test_disbursement(loan, keep_dependencies=keep_dependencies)
    if not keep_dependencies:
        remove_test_loan(loan)
