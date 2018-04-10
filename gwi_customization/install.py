# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import frappe

settings_accounts = {
    'loan_account': {
        'account_name': 'Loans on Collateral',
        'parent_account': 'Loans and Advances (Assets)',
    },
    'interest_income_account': {
        'account_name': 'Interests on Loans',
        'account_type': 'Income Account',
        'parent_account': 'Direct Income',
    },
}


def _create_account(doc, company_name, company_abbr):
    account = frappe.get_doc({
        'doctype': 'Account',
        'account_name': doc['account_name'],
        'parent_account': "{} - {}".format(
            doc['parent_account'], company_abbr
        ),
        'is_group': 0,
        'company': company_name,
        'account_type': doc.get('account_type'),
    }).insert(ignore_if_duplicate=True)
    return account.name


def before_tests():
    frappe.clear_cache()
    frappe.get_test_records('Company')
    frappe.get_test_records('Cost Center')
    settings = frappe.get_single('Microfinance Loan Settings')
    settings.update({
        'mode_of_payment': 'Cash',
        'effective_date': '2017-08-01',
        'npa_duration': 3,
        'cost_center': 'Main - _TC',
    })
    for key, value in settings_accounts.items():
        settings.update({
            key: _create_account(value, '_Test Company', '_TC'),
        })
    settings.save()
    frappe.db.commit()


def after_wizard_complete(args=None):
    """
    Create new accounts and set Loan Settings.
    """
    if frappe.defaults.get_global_default('country') != "India":
        return
    settings = frappe.get_single('Microfinance Loan Settings')
    settings.update({
        'mode_of_payment': 'Cash',
        'effective_date': '2017-08-01',
        'npa_duration': 3,
        'cost_center': frappe.db.get_value(
            'Company', args.get('company_name'), 'cost_center',
        ),
    })
    for key, value in settings_accounts.items():
        settings.update({
            key: _create_account(
                value, args.get('company_name'), args.get('company_abbr'),
            )
        })
    settings.save()
