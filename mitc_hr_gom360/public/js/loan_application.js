frappe.ui.form.on('Loan Application', {
    refresh: function(frm) {
        frm.trigger('toggle_custom_repayment_period');
    },
    repayment_method: function(frm) {
        frm.trigger('toggle_custom_repayment_period');
    },
    custom_rep_repayment_period_in_months: function(frm) {
        if (frm.doc.repayment_method === 'Repay Equal Principal') {
            frm.set_value('repayment_periods', frm.doc.custom_rep_repayment_period_in_months);
        }
    },
    toggle_custom_repayment_period: function(frm) {
        const is_equal_principal = frm.doc.repayment_method === 'Repay Equal Principal';

        // Show/Hide custom_rep_repayment_period_in_months based on selection
        frm.toggle_display('custom_rep_repayment_period_in_months', is_equal_principal);
        frm.toggle_reqd('custom_rep_repayment_period_in_months', is_equal_principal);

        if (is_equal_principal && frm.doc.custom_rep_repayment_period_in_months) {
            frm.set_value('repayment_periods', frm.doc.custom_rep_repayment_period_in_months);
        }
    }
});
