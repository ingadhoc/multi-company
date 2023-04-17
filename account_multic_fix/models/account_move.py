##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, Command


class AccountMove(models.Model):
    _inherit = "account.move"


    @api.onchange('company_id')
    def _inverse_company_id(self):
        """ Aquí corregimos el problema de cambiar automaticamente los impuestos de una factura
        cuando se cambia la compania de la misma, para que tenga impuestos de la compania correcta.
        Si no hacemos esto odoo nos da error y nos dice que no podemos usar impuestos de otra compania
        """
        super()._inverse_company_id()

        lines = self.invoice_line_ids.filtered(lambda x: x.tax_ids.company_id != self.company_id)
        if lines:
            move = self
            container = {'records': move}
            with move._check_balanced(container):
                with move._sync_dynamic_lines(container):
                    lines._compute_tax_ids()
                    for line in lines:
                        line.write({'tax_ids': [Command.set(line.tax_ids.ids)]})

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        # we override this method to add filter by companies in the env instead of the company of the user
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_ids = self.env.companies.ids
            domain = [('company_id', 'in', company_ids), ('type', '=', journal_type)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)
