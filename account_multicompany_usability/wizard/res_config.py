# -*- coding: utf-8 -*-
from openerp import api, fields, models
# from openerp.exceptions import UserError


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    default_sale_tax_ids = fields.Many2many(
        'account.tax',
        'config_tax_default_rel',
        'account_id', 'tax_id',
        string="Default Sale Taxes",
        help="This sale tax will be assigned by default on new products.",
    )
    default_purchase_tax_ids = fields.Many2many(
        'account.tax',
        'config_purchase_tax_default_rel',
        'account_id', 'purchase_tax_id',
        string="Default Purchase Taxes",
        help="This purchase tax will be assigned by default on new products.",
    )

    @api.multi
    @api.onchange('company_id')
    def change_company_get_default_taxes(self):
        ir_values = self.env['ir.values']
        taxes_ids = ir_values.get_default(
            'product.template', 'taxes_id', company_id=self.company_id.id)
        supplier_taxes_ids = ir_values.get_default(
            'product.template', 'supplier_taxes_id',
            company_id=self.company_id.id)
        self.default_sale_tax_ids = taxes_ids
        self.default_purchase_tax_id = supplier_taxes_ids

    @api.multi
    def set_product_taxes(self):
        """
        We overwrite original function so we can set multiple default taxes
        """
        # res = super(AccountConfigSettings, self).onchange_company_id()
        ir_values_obj = self.env['ir.values']
        if self.default_sale_tax_ids:
            ir_values_obj.sudo().set_default(
                'product.template',
                "taxes_id",
                self.default_sale_tax_ids.ids,
                for_all_users=True,
                company_id=self.company_id.id)
        if self.default_purchase_tax_ids:
            ir_values_obj.sudo().set_default(
                'product.template',
                "supplier_taxes_id",
                self.default_purchase_tax_ids.ids,
                for_all_users=True,
                company_id=self.company_id.id)
