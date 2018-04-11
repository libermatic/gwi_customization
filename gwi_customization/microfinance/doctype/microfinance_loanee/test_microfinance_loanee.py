# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest


class TestMicrofinanceLoanee(unittest.TestCase):
    def tearDown(self):
        remove_test_loanee()

    def test_creates_customer(self):
        loanee = create_test_loanee()
        customer = frappe.get_doc('Customer', loanee.customer)
        self.assertIsNotNone(customer)
        self.assertEqual(loanee.customer, customer.name)
        keys = ['salutation', 'customer_name', 'gender']
        for k in keys:
            self.assertEqual(loanee.get(k), customer.get(k))

    def test_updates_customer(self):
        loanee = create_test_loanee()
        loanee.update({
            'salutation': 'Dr',
            'customer_name': '_Test Another',
            'gender': 'Male',
        })
        loanee.save()
        customer = frappe.get_doc('Customer', loanee.customer)
        keys = ['salutation', 'customer_name', 'gender']
        for k in keys:
            self.assertEqual(loanee.get(k), customer.get(k))

    def test_updates_doc_on_customer_update(self):
        pre_loanee = create_test_loanee()
        customer = frappe.get_doc('Customer', pre_loanee.customer)
        customer.update({
            'salutation': 'Dr',
            'customer_name': '_Test Another',
            'gender': 'Male',
        })
        frappe.clear_cache()
        customer.save()
        keys = ['salutation', 'customer_name', 'gender']
        pre_loanee.clear_cache()
        loanee = frappe.get_value(
            'Microfinance Loanee',
            pre_loanee.name,
            fieldname=keys,
            as_dict=True,
        )
        for k in keys:
            self.assertEqual(loanee.get(k), customer.get(k))

    def test_links_to_existing_customer(self):
        customer = frappe.get_doc({
            'doctype': 'Customer',
            'name': '_Test Loan Customer',
            'customer_name': '_Test Another',
        }).insert()
        loanee = create_test_loanee(customer_name='_Test Another')
        self.assertEqual(customer.name, loanee.customer)


def create_test_loanee(**kwargs):
    args = frappe._dict(kwargs)
    fields = {
        'salutation': args.salutation or 'Ms',
        'customer_name': args.customer_name or '_Test Loanee',
        'gender': args.gender or 'Female',
        'date_of_birth': args.date_of_birth or '1986-08-19',
        'relation_type': args.relation_type or 'Wife',
        'related_to': args.related_to or '_Test Loanee Spouse',
        'id_type': args.id_type or 'Aadhaar',
        'id_no': args.id_no or '444455556666',
        'nominee_name': args.nominee_name or '_Test Loanee Nominee',
        'relation_to_nominee': args.relation_to_nominee or '_Test Employer',
        'service_type': args.service_type or 'Full Time',
        'department': args.department or '_Test Department',
        'posting': args.posting or '_Test Posting',
        'designation': args.designation or '_Test Designation',
        'date_of_joining': args.date_of_joining or '2010-12-12',
        'date_of_retirement': args.date_of_retirement or '2046-08-19',
        'basic_pay': args.basic_pay or '15000.0',
        'total_emolument': args.total_emolument or '50000.0',
        'net_salary_amount': args.net_salary_amount or '40000.0',
        'name_of_bank': args.name_of_bank or 'SBI',
        'account_no': args.account_no or '1034445555',
        'card_no': args.card_no or '44445555',
    }
    doc = frappe.new_doc('Microfinance Loanee')
    doc.update(fields)
    if not args.do_not_insert:
        try:
            doc.insert()
        except frappe.UniqueValidationError:
            existing = frappe.get_doc(
                'Microfinance Loanee',
                {'customer_name': args.customer_name or '_Test Loanee'},
            )
            existing.update(fields)
            existing.save()
            return existing
    return doc


def remove_test_loanee(customer_name='_Test Loanee, _Test Another'):
    filters = [
        ['customer_name', 'in', customer_name]
    ]
    loanees = map(
        lambda x: x.update({'doctype': 'Microfinance Loanee'}),
        frappe.get_all('Microfinance Loanee', filters=filters)
    )
    customers = map(
        lambda x: x.update({'doctype': 'Customer'}),
        frappe.get_all('Customer', filters=filters)
    )
    for doc in loanees + customers:
        frappe.delete_doc(
            doctype=doc.doctype, name=doc.name, force=True
        )
