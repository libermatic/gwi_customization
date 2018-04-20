// Copyright (c) 2016, Libermatic and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['Microfinance Asset Health'] = {
  filters: [
    {
      fieldname: 'loan_plan',
      label: __('Loan Plan'),
      fieldtype: 'Link',
      options: 'Microfinance Loan Plan',
    },
    {
      fieldname: 'customer',
      label: __('Customer'),
      fieldtype: 'Link',
      options: 'Customer',
    },
    {
      fieldname: 'name',
      label: __('Loan'),
      fieldtype: 'Link',
      options: 'Microfinance Loan',
      get_query: doc => ({ filters: { docstatus: 1 } }),
    },
    {
      fieldname: 'display',
      label: __('Display'),
      fieldtype: 'Select',
      options: 'NPA Only\nExisting Loans\nAll Loans',
      default: 'NPA Only',
    },
  ],
};
