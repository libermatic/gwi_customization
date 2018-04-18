// Copyright (c) 2016, Libermatic and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['Microfinance Loan Summary'] = {
  filters: [
    {
      fieldname: 'display',
      label: __('Display'),
      fieldtype: 'Select',
      options: 'Existing Loans\nAll Loans',
      default: 'Existing Loans',
    },
    {
      fieldname: 'loan_plan',
      label: __('Loan Plan'),
      fieldtype: 'Link',
      options: 'Microfinance Loan Plan',
    },
  ],
};
