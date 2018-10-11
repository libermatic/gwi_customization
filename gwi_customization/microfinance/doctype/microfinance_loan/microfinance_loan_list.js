frappe.listview_settings['Microfinance Loan'] = {
  add_fields: ['disbursement_status', 'recovery_status'],
  get_indicator: function({ disbursement_status, recovery_status }) {
    if (recovery_status === 'NPA') {
      return [__('NPA'), 'red', 'recovery_status,=,NPA'];
    }
    if (disbursement_status === 'Sanctioned') {
      return [__('Sanctioned'), 'darkgrey', 'disbursement_status,=,Sanctioned'];
    }
    if (disbursement_status === 'Partially Disbursed') {
      return [
        __('Pending'),
        'orange',
        'disbursement_status,=,Partially Disbursed',
      ];
    }
    if (
      disbursement_status === 'Fully Disbursed' &&
      recovery_status === 'Not Started'
    ) {
      return [
        __('Disbursed'),
        'yellow',
        'disbursement_status,=,Fully Disbursed|recovery_status,=,Not Started',
      ];
    }
    if (
      disbursement_status === 'Fully Disbursed' &&
      recovery_status === 'In Progress'
    ) {
      return [
        __('In Progress'),
        'lightblue',
        'disbursement_status,=,Fully Disbursed|recovery_status,=,In Progress',
      ];
    }
    if (
      disbursement_status === 'Fully Disbursed' &&
      recovery_status === 'Repaid'
    ) {
      return [
        __('Cleared'),
        'blue',
        'disbursement_status,=,Fully Disbursed|recovery_status,=,Repaid',
      ];
    }
  },
};
