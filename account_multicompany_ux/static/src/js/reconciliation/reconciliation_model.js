odoo.define('account.ReconciliationModel.multicompany', function (require) {
    "use strict";

    var ReconciliationModel = require('account.ReconciliationModel');
    ReconciliationModel.StatementModel.include({
        _changePartner: function (handle, partner_id) {
            this._super(handle, partner_id);
            var self = this;
            return this._rpc({
                model: 'res.partner',
                method: 'read',
                args: [partner_id, ["property_account_receivable_id",
                                    "property_account_payable_id"]],
                context: {
                    force_company: self.lines[handle].st_line.company_id,
                },
            }).then(function (result) {
                if (result.length > 0) {
                    var line = self.getLine(handle);
                    self.lines[handle].st_line.open_balance_account_id = line.balance.amount < 0 ? result[0].property_account_payable_id[0] : result[0].property_account_receivable_id[0];
                }
            });
        },
    });
});
