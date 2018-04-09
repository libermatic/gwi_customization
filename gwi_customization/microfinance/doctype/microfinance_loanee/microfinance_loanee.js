// Copyright (c) 2018, Libermatic and contributors
// For license information, please see license.txt

frappe.ui.form.on('Microfinance Loanee', {
  refresh: function(frm) {
    if (!frm.doc.__islocal) {
      if (frm.fields_dict['address_html'] && 'addr_list' in frm.doc.__onload) {
        $(frm.fields_dict['address_html'].wrapper)
          .html(frappe.render_template('address_list', cur_frm.doc.__onload))
          .find('.btn-address')
          .on('click', function() {
            frappe.dynamic_link = {
              doc: frm.doc,
              fieldname: 'customer',
              doctype: 'Customer',
            };
            frappe.new_doc('Address', { address_type: 'Permanent' });
          });
      }
    } else {
      $(frm.fields_dict['address_html'].wrapper).html('');
    }
  },
});
