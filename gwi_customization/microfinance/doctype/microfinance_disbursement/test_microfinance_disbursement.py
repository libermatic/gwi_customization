# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from gwi_customization.microfinance.doctype.microfinance_loan.\
    test_microfinance_loan import create_test_loan, remove_test_loan
from gwi_customization.microfinance.utils import get_gle_by

get_disburement_gle = get_gle_by('Microfinance Disbursement')


class TestMicrofinanceDisbursement(unittest.TestCase):
    def tearDown(self):
        remove_test_disbursement()

    def test_totals(self):
        disbursement = create_test_disbursement(
            amount=50000.0,
            charges=[
                {'charge': '_Test Charge 1', 'charge_amount': 150.0},
                {'charge': '_Test Charge 2', 'charge_amount': 5000.0},
            ]
        )
        self.assertEqual(disbursement.total_disbursed, 50000.0)
        self.assertEqual(disbursement.total_charges, 5150.0)

    def test_opening_entries(self):
        disbursement = create_test_disbursement(
            amount=80000.0,
            is_opening=True,
            recovered_amount=20000.0,
        )
        self.assertEqual(disbursement.total_disbursed, 100000.0)

    def test_raises_when_total_disbursed_exceeds_outstanding(self):
        create_test_loan(
            loan_no='_Test Loan 1',
            loan_principal=50000.0,
        )
        with self.assertRaises(frappe.exceptions.ValidationError):
            create_test_disbursement(
                skip_dependencies=True,
                amount=60000.0,
                do_not_submit=True,
            )

    def test_raises_when_posting_date_is_before_loan_posting_date(self):
        create_test_loan(
            loan_no='_Test Loan 1',
            posting_date='2017-12-12',
        )
        with self.assertRaises(frappe.exceptions.ValidationError):
            create_test_disbursement(
                skip_dependencies=True,
                posting_date='2017-11-11',
                do_not_submit=True,
            )

    def test_updates_loan_status(self):
        disbursement = create_test_disbursement()
        disbursement_status = frappe.get_value(
            'Microfinance Loan', disbursement.loan, 'disbursement_status'
        )
        self.assertEqual(disbursement_status, 'Fully Disbursed')

    def test_updates_loan_status_for_partial(self):
        create_test_loan(
            loan_no='_Test Loan 1',
            loan_principal=100000.0,
        )
        disbursement = create_test_disbursement(
            skip_dependencies=True,
            amount=50000.0,
        )
        disbursement_status = frappe.get_value(
            'Microfinance Loan', disbursement.loan, 'disbursement_status'
        )
        self.assertEqual(disbursement_status, 'Partially Disbursed')

    def test_gle(self):
        disbursement = create_test_disbursement(amount=50000.0, charges=[])
        exp_gle = dict((d[0], d) for d in [
            ['Microfinance Loans - _TC', 50000, 0, None],
            ['Cash - _TC', 0, 50000, '_Test Loanee 1'],
        ])
        gl_entries = get_disburement_gle(disbursement.name)
        self.assertEqual(len(gl_entries), 2)
        for gle in gl_entries:
            self.assertEquals(exp_gle[gle.account][0], gle.account)
            self.assertEquals(exp_gle[gle.account][1], gle.debit)
            self.assertEquals(exp_gle[gle.account][2], gle.credit)
            self.assertEquals(exp_gle[gle.account][3], gle.against)
            self.assertEquals(disbursement.loan, gle.against_voucher)

    def test_cancel_on_gle(self):
        disbursement = create_test_disbursement(amount=50000.0, charges=[])
        disbursement.cancel()
        gl_entries = get_disburement_gle(disbursement.name)
        self.assertEqual(len(gl_entries), 0)

    def test_gle_with_charges(self):
        disbursement = create_test_disbursement(
            amount=50000.0,
            charges=[
                {'charge': '_Test Charge 1', 'charge_amount': 150.0},
                {'charge': '_Test Charge 2', 'charge_amount': 5000.0},
            ]
        )
        exp_gle = dict((d[0], d) for d in [
            ['Microfinance Loans - _TC', 50000, 0, None],
            ['Service - _TC', 0, 5150, None],
            ['Cash - _TC', 5150, 50000, '_Test Loanee 1'],
        ])
        gl_entries = get_disburement_gle(disbursement.name)
        self.assertEqual(len(gl_entries), 3)
        for gle in gl_entries:
            self.assertEquals(exp_gle[gle.account][0], gle.account)
            self.assertEquals(exp_gle[gle.account][1], gle.debit)
            self.assertEquals(exp_gle[gle.account][2], gle.credit)
            self.assertEquals(exp_gle[gle.account][3], gle.against)

    def test_gle_for_opening(self):
        disbursement = create_test_disbursement(
            amount=30000.0,
            is_opening=1,
            recovered_amount=20000.0
        )
        exp_gle = dict((d[0], d) for d in [
            ['Microfinance Loans - _TC', 50000, 20000, None],
            ['Temporary Opening - _TC', 20000, 20000, None],
            ['Cash - _TC', 0, 30000, '_Test Loanee 1'],
        ])
        gl_entries = get_disburement_gle(disbursement.name)
        self.assertEqual(len(gl_entries), 3)
        for gle in gl_entries:
            self.assertEquals(exp_gle[gle.account][0], gle.account)
            self.assertEquals(exp_gle[gle.account][1], gle.debit)
            self.assertEquals(exp_gle[gle.account][2], gle.credit)
            self.assertEquals(exp_gle[gle.account][3], gle.against)


def create_test_disbursement(**kwargs):
    args = frappe._dict(kwargs)
    if not args.skip_dependencies:
        create_test_loan(
            loan_no=args.loan or '_Test Loan 1',
            loan_principal=args.loan_principal or 100000.0,
        )
    doc = frappe.new_doc('Microfinance Disbursement')
    doc.update({
        'loan': args.loan or '_Test Loan 1',
        'posting_date': args.posting_date or '2017-08-20',
        'amount': args.amount or 100000.0,
        'mode_of_payment': args.mode_of_payment or 'Cash',
    })
    if args.is_opening:
        doc.update({
            'is_opening': 'Yes',
            'recovered_amount': args.recovered_amount or 20000.0,
        })
    if args.charges:
        for item in args.charges:
            doc.append('charges', item)
    if args.mode_of_payment == 'Cheque':
        doc.update({
            'cheque_no': args.cheque_no or 'ABCABC',
            'cheque_date': args.cheque_date or '2017-08-20',
        })
    if not args.do_not_insert:
        doc.insert(ignore_if_duplicate=True)
        if not args.do_not_submit:
            doc.submit()
    return doc


def remove_test_disbursement(loan='_Test Loan 1', keep_dependencies=False):
    disbursements = frappe.get_all(
        'Microfinance Disbursement',
        filters=[['loan', 'in', loan]],
    )
    for doc in disbursements:
        try:
            dis = frappe.get_doc('Microfinance Disbursement', doc.name)
            if dis.docstatus == 1:
                dis.cancel()
        except frappe.DoesNotExistError:
            pass
        frappe.delete_doc(
            doctype='Microfinance Disbursement', name=doc.name, force=True
        )
    if not keep_dependencies:
        remove_test_loan('_Test Loan 1')
