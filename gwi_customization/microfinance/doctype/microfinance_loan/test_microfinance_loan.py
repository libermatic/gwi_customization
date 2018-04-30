# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from gwi_customization.microfinance.doctype.microfinance_loanee.\
    test_microfinance_loanee import create_test_loanee, remove_test_loanee
# from gwi_customization.microfinance.doctype.microfinance_disbursement.\
#     test_microfinance_disbursement \
#     import create_test_disbursement, remove_test_disbursement

test_dependencies = ['Microfinance Loan Plan']


class TestMicrofinanceLoan(unittest.TestCase):
    def tearDown(self):
        remove_test_loan()

    def test_statuses(self):
        loan = create_test_loan()
        self.assertEqual(loan.disbursement_status, 'Sanctioned')
        self.assertEqual(loan.recovery_status, 'Not Started')

    def test_billing_start_date(self):
        loan = create_test_loan(posting_date='2017-11-11')
        self.assertEqual(
            loan.billing_start_date, frappe.utils.getdate('2017-12-01')
        )

    def test_loan_plan_values(self):
        loan = create_test_loan(do_not_submit=True)
        self.assertEqual(loan.rate_of_interest, 10.0)
        self.assertEqual(loan.rate_of_late_charges, 5.0)
        self.assertEqual(loan.calculation_slab, 10000.0)

    def test_accounts(self):
        interest_income_account, loan_account = frappe.get_value(
            'Microfinance Loan Settings',
            None,
            ['interest_income_account', 'loan_account']
        )
        loan = create_test_loan(do_not_submit=True)
        self.assertEqual(
            loan.loan_account, loan_account
        )
        self.assertEqual(
            loan.interest_income_account, interest_income_account
        )

    def test_raises_when_recovery_more_than_principal(self):
        with self.assertRaises(frappe.exceptions.ValidationError):
            create_test_loan(
                loan_principal=10000.0,
                recovery_amount=10001.0,
            )

    def test_principal_more_than_allowed(self):
        create_test_loanee(
            customer_name='_Test Loanee 1',
            date_of_retirement='2018-12-12',
            net_salary_amount=3000.0,
        )
        with self.assertRaises(frappe.exceptions.ValidationError):
            create_test_loan(
                skip_dependencies=True,
                posting_date='2017-12-01',
                loan_principal=11001.0,
                recovery_amount=1500.0,
            )

    def test_recovery_less_than_allowed(self):
        create_test_loanee(
            customer_name='_Test Loanee 1',
            date_of_retirement='2018-12-12',
            net_salary_amount=3000.0,
        )
        with self.assertRaises(frappe.exceptions.ValidationError):
            create_test_loan(
                skip_dependencies=True,
                posting_date='2017-12-01',
                loan_principal=11000.0,
                recovery_amount=999.0,
            )

    def test_total_outstanding_more_than_allowed(self):
        create_test_loanee(
            customer_name='_Test Loanee 1',
            date_of_retirement='2018-12-12',
            net_salary_amount=3000.0,
        )
        create_test_loan(
            skip_dependencies=True,
            posting_date='2017-12-01',
            loan_principal=6000.0,
            recovery_amount=600.0,
        )
        disbursement = frappe.get_doc({
            'doctype': 'Microfinance Disbursement',
            'loan': '_TEST LOAN',
            'posting_date': '2017-12-02',
            'amount': 6000.0,
            'mode_of_payment': 'Cash',
        })
        disbursement.insert()
        disbursement.submit()
        with self.assertRaises(frappe.exceptions.ValidationError):
            create_test_loan(
                skip_dependencies=True,
                loan_no='_Test Loan Another',
                posting_date='2018-02-12',
                loan_principal=6000.0,
                recovery_amount=700.0,
            )
        disbursement.cancel()
        frappe.delete_doc(
            'Microfinance Disbursement', name=disbursement.name, force=True
        )


def create_test_loan(**kwargs):
    args = frappe._dict(kwargs)
    if not args.skip_dependencies:
        create_test_loanee(customer_name=args.customer or '_Test Loanee 1')
    doc = frappe.new_doc('Microfinance Loan')
    doc.update({
        'loan_no': args.loan_no or '_Test Loan',
        'customer': args.customer or '_Test Loanee 1',
        'posting_date': args.posting_date or '2017-08-19',
        'company': args.company or '_Test Company',
        'loan_plan': args.loan_plan or '_Test Loan Plan Basic',
        'loan_principal': args.loan_principal or 100000.0,
        'recovery_amount': args.recovery_amount or 2000.0,
    })
    if not args.do_not_insert:
        doc.insert()
        if not args.do_not_submit:
            doc.submit()
    return doc


def remove_test_loan(loan='_Test Loan', keep_dependencies=False):
    try:
        doc = frappe.get_doc('Microfinance Loan', loan)
        if doc.docstatus == 1:
            doc.cancel()
    except frappe.DoesNotExistError:
        pass
    frappe.delete_doc_if_exists(
        'Microfinance Loan', loan, force=True
    )
    if not keep_dependencies:
        remove_test_loanee('_Test Loanee 1')
