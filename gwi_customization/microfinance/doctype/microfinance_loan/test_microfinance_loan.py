# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from gwi_customization.microfinance.doctype.microfinance_loanee.\
    test_microfinance_loanee import create_test_loannee, remove_test_loanee

test_dependencies = ['Microfinance Loan Plan']


class TestMicrofinanceLoan(unittest.TestCase):
    def setUp(self):
        create_test_loannee(customer_name='_Test Loanee 1')

    def tearDown(self):
        try:
            loan = frappe.get_doc('Microfinance Loan', '_TEST LOAN')
            if loan.docstatus == 1:
                loan.cancel()
        except frappe.DoesNotExistError:
            pass
        frappe.delete_doc_if_exists(
            'Microfinance Loan', '_TEST LOAN', force=1
        )
        remove_test_loanee('_Test Loanee 1')

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
        loan_account, interest_income_account = frappe.get_value(
            'Microfinance Loan Settings',
            None,
            ['loan_account', 'interest_income_account']
        )
        loan = create_test_loan(do_not_submit=True)
        self.assertEqual(
            loan.loan_account, loan_account
        )
        self.assertEqual(
            loan.interest_income_account, interest_income_account
        )


def create_test_loan(**kwargs):
    args = frappe._dict(kwargs)
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
