# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.utils import getdate
import unittest
from gwi_customization.microfinance.doctype.microfinance_loan.\
    test_microfinance_loan import create_test_loan, remove_test_loan
from gwi_customization.microfinance.doctype.microfinance_disbursement.\
    test_microfinance_disbursement import (
        create_test_disbursement, remove_test_disbursement
    )
from gwi_customization.microfinance.doctype.microfinance_loan_interest.\
    test_microfinance_loan_interest import remove_test_interest
from gwi_customization.microfinance.utils import get_gle_by

get_recovery_gle = get_gle_by('Microfinance Recovery')


class TestMicrofinanceRecovery(unittest.TestCase):
    def tearDown(self):
        remove_test_recovery()

    def test_totals(self):
        recovery = create_test_recovery(
            total_amount=15000.0,
            principal_amount=5000.0,
            charges=[
                {'charge': '_Test Charge 1', 'charge_amount': 150.0},
                {'charge': '_Test Charge 2', 'charge_amount': 5000.0},
            ]
        )
        self.assertEqual(recovery.total_interests, 10000.0)
        self.assertEqual(recovery.total_charges, 5150.0)

    def test_interests(self):
        recovery = create_test_recovery(
            posting_date='2017-09-17',
            total_amount=15000.0,
            principal_amount=5000.0,
        )
        self.assertEqual(len(recovery.periods), 1)
        self.assertEqual(recovery.periods[0].billed_amount, 10000)
        self.assertEqual(recovery.periods[0].outstanding_amount, 10000)
        self.assertEqual(recovery.periods[0].allocated_amount, 10000)
        period = frappe.get_doc(
            'Microfinance Loan Interest', recovery.periods[0].ref_interest
        ).as_dict()
        to_check = {
            'loan': '_Test Loan 1',
            'posting_date': getdate('2017-09-17'),
            'period': 'Aug, 2017',
            'start_date': getdate('2017-08-19'),
            'end_date': getdate('2017-08-31'),
            'billed_amount': 10000,
            'paid_amount': 10000,
        }
        for k, v in to_check.items():
            self.assertEqual(v, period.get(k))

    def test_interests_partial(self):
        recovery = create_test_recovery(
            total_amount=12000.0,
            principal_amount=5000.0,
        )
        self.assertEqual(recovery.periods[0].billed_amount, 10000)
        self.assertEqual(recovery.periods[0].outstanding_amount, 10000)
        self.assertEqual(recovery.periods[0].allocated_amount, 7000)
        period = frappe.get_doc(
            'Microfinance Loan Interest', recovery.periods[0].ref_interest
        )
        to_check = {
            'billed_amount': 10000,
            'paid_amount': 7000,
        }
        for k, v in to_check.items():
            self.assertEqual(v, period.get(k))

    def test_interests_multiple(self):
        recovery = create_test_recovery(
            total_amount=22000.0,
            principal_amount=5000.0,
        )
        period = frappe.get_doc(
            'Microfinance Loan Interest', recovery.periods[1].ref_interest
        ).as_dict()
        to_check = {
            'loan': '_Test Loan 1',
            'posting_date': getdate('2017-09-17'),
            'period': 'Sep, 2017',
            'start_date': getdate('2017-09-01'),
            'end_date': getdate('2017-09-30'),
            'billed_amount': 10000,
            'paid_amount': 7000,
        }
        for k, v in to_check.items():
            self.assertEqual(v, period.get(k))

    def test_interests_multiple_paid_amounts(self):
        create_test_recovery(
            total_amount=22000.0,
            principal_amount=5000.0,
        )
        exp_amounts = dict((d[0], d) for d in [
            ['_Test Loan 1/2017-08', 10000],
            ['_Test Loan 1/2017-09', 7000],
        ])
        periods = frappe.get_all(
            'Microfinance Loan Interest',
            filters={'loan': '_Test Loan 1'},
            fields=['name', 'paid_amount'],
        )
        self.assertEqual(len(periods), 2)
        for per in periods:
            self.assertEquals(
                exp_amounts[per.get('name')][0], per.get('name')
            )
            self.assertEquals(
                exp_amounts[per.get('name')][1], per.get('paid_amount')
            )

    def test_interests_with_previous_entries(self):
        create_test_recovery(
            total_amount=32000.0,
            principal_amount=15000.0,
        )
        create_test_recovery(
            skip_dependencies=True,
            total_amount=12000.0,
        )
        exp_amounts = dict((d[0], d) for d in [
            ['_Test Loan 1/2017-08', 10000],
            ['_Test Loan 1/2017-09', 10000],
            ['_Test Loan 1/2017-10', 9000],
        ])
        periods = frappe.get_all(
            'Microfinance Loan Interest',
            filters={'loan': '_Test Loan 1'},
            fields=['name', 'paid_amount', 'billed_amount'],
        )
        self.assertEqual(len(periods), 3)
        for per in periods:
            self.assertEquals(
                exp_amounts[per.get('name')][0], per.get('name')
            )
            self.assertEquals(
                exp_amounts[per.get('name')][1], per.get('paid_amount')
            )

    def test_cancel_on_interests(self):
        recovery = create_test_recovery(
            total_amount=22000.0,
            principal_amount=5000.0,
        )
        recovery.cancel()
        periods = frappe.get_all(
            'Microfinance Loan Interest',
            filters={'loan': '_Test Loan 1'},
            fields=['paid_amount'],
        )
        self.assertEqual(len(periods), 2)
        for per in periods:
            self.assertEqual(per.get('paid_amount'), 0)

    def test_updates_loan_status(self):
        recovery = create_test_recovery()
        recovery_status = frappe.get_value(
            'Microfinance Loan', recovery.loan, 'recovery_status'
        )
        self.assertEqual(recovery_status, 'In Progress')

    def test_updates_loan_status_for_repaid(self):
        recovery = create_test_recovery(
            principal_amount=100000
        )
        recovery_status = frappe.get_value(
            'Microfinance Loan', recovery.loan, 'recovery_status'
        )
        self.assertEqual(recovery_status, 'Repaid')

    def test_gle(self):
        recovery = create_test_recovery(principal_amount=10000.0)
        exp_gle = dict((d[0], d) for d in [
            ['Microfinance Loans - _TC', 0, 10000, None],
            ['Cash - _TC', 10000, 0, '_Test Loanee 1'],
        ])
        gl_entries = get_recovery_gle(recovery.name)
        self.assertEqual(len(gl_entries), 2)
        for gle in gl_entries:
            self.assertEquals(exp_gle[gle.account][0], gle.account)
            self.assertEquals(exp_gle[gle.account][1], gle.debit)
            self.assertEquals(exp_gle[gle.account][2], gle.credit)
            self.assertEquals(exp_gle[gle.account][3], gle.against)
            self.assertEquals(recovery.loan, gle.against_voucher)

    def test_cancel_on_gle(self):
        recovery = create_test_recovery()
        recovery.cancel()
        gl_entries = get_recovery_gle(recovery.name)
        self.assertEqual(len(gl_entries), 0)

    def test_gle_with_charges(self):
        recovery = create_test_recovery(
            principal_amount=10000.0,
            charges=[
                {'charge': '_Test Charge 1', 'charge_amount': 150.0},
                {'charge': '_Test Charge 2', 'charge_amount': 5000.0},
            ]
        )
        exp_gle = dict((d[0], d) for d in [
            ['Microfinance Loans - _TC', 0, 10000, None],
            ['Service - _TC', 0, 5150, None],
            ['Cash - _TC', 15150, 0, '_Test Loanee 1'],
        ])
        gl_entries = get_recovery_gle(recovery.name)
        self.assertEqual(len(gl_entries), 3)
        for gle in gl_entries:
            self.assertEquals(exp_gle[gle.account][0], gle.account)
            self.assertEquals(exp_gle[gle.account][1], gle.debit)
            self.assertEquals(exp_gle[gle.account][2], gle.credit)
            self.assertEquals(exp_gle[gle.account][3], gle.against)

    def test_gle_with_interests(self):
        recovery = create_test_recovery(
            total_amount=15000.0,
            principal_amount=5000.0,
        )
        exp_gle = dict((d[0], d) for d in [
            ['Microfinance Loans - _TC', 0, 15000, None],
            ['Cash - _TC', 15000, 0, '_Test Loanee 1'],
        ])
        gl_entries = get_recovery_gle(recovery.name)
        self.assertEqual(len(gl_entries), 2)
        for gle in gl_entries:
            self.assertEquals(exp_gle[gle.account][0], gle.account)
            self.assertEquals(exp_gle[gle.account][1], gle.debit)
            self.assertEquals(exp_gle[gle.account][2], gle.credit)
            self.assertEquals(exp_gle[gle.account][3], gle.against)


def create_test_recovery(**kwargs):
    args = frappe._dict(kwargs)
    if not args.skip_dependencies:
        create_test_loan(
            loan_no=args.loan or '_Test Loan 1',
            loan_plan=args.loan_plan or '_Test Loan Plan Basic',
            loan_principal=args.loan_principal or 100000.0,
        )
        create_test_disbursement(
            loan=args.loan or '_Test Loan 1',
            amount=args.amount or args.loan_principal or 100000.0,
            skip_dependencies=True,
        )
    doc = frappe.new_doc('Microfinance Recovery')
    doc.update({
        'loan': args.loan or '_Test Loan 1',
        'posting_date': args.posting_date or '2017-09-17',
        'total_amount': args.total_amount or args.principal_amount or 15000.0,
        'principal_amount': args.principal_amount or 0,
        'mode_of_payment': args.mode_of_payment or 'Cash',
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


def remove_test_recovery(loan='_Test Loan 1', keep_dependencies=False):
    recoveries = frappe.get_all(
        'Microfinance Recovery', filters=[['loan', 'in', loan]],
    )
    for doc in recoveries:
        try:
            rec = frappe.get_doc('Microfinance Recovery', doc.name)
            if rec.docstatus == 1:
                rec.cancel()
        except frappe.DoesNotExistError:
            pass
        frappe.delete_doc(
            doctype='Microfinance Recovery', name=doc.name, force=True
        )
    remove_test_interest(loan, keep_dependencies=keep_dependencies)
    remove_test_disbursement(loan, keep_dependencies=keep_dependencies)
    if not keep_dependencies:
        remove_test_loan(loan)
