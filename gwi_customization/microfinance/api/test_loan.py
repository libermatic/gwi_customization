# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from frappe.utils import getdate
from gwi_customization.microfinance.api.loan import calculate_principal


class TestLoan(unittest.TestCase):
    def test_calculate_principal(self):
        actual = calculate_principal(
            20000.0, '_Test Loan Plan Basic', '2030-08-19', '2017-12-12'
        )
        expected = {
            'principal': 400000.0,
            'expected_eta': getdate('2022-12-31'),
            'duration': 60,
            'recovery_amount': 6666.67,
            'initial_interest': 40000.0,
        }
        self.assertEqual(actual, expected)

    def test_calculate_principal_end_date_before_loan_plan_max_duration(self):
        actual = calculate_principal(
            20000.0, '_Test Loan Plan Basic', '2020-08-19', '2017-12-12',
        )
        expected = {
            'principal': 206666.67,
            'expected_eta': getdate('2020-07-31'),
            'duration': 31,
            'recovery_amount': 6666.67,
            'initial_interest': 21000.0,
        }
        self.assertEqual(actual, expected)

    def test_calculate_principal_force_max_duration(self):
        actual = calculate_principal(
            20000.0, '_Test Loan Plan Eco', '2020-08-19', '2017-12-12'
        )
        expected = {
            'principal': 300000.0,
            'expected_eta': getdate('2022-12-31'),
            'duration': 60,
            'recovery_amount': 5000.0,
            'initial_interest': 15000.0,
        }
        self.assertEqual(actual, expected)
