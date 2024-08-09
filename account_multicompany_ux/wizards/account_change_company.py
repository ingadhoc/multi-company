##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _


class AccountChangeCurrency(models.TransientModel):
    _name = 'account.change.company'
    _description = 'Change Company'

    @api.model
    def get_move(self):
        move = self.env['account.move'].browse(
            self._context.get('active_id', False))
        return move

    move_id = fields.Many2one('account.move', default=get_move)
    company_ids = fields.Many2many('res.company', string='Companies', compute='_compute_company_ids')
    company_id = fields.Many2one(
        'res.company', required=True, ondelete='cascade',
        compute='_compute_company', store=True, readonly=False)
    journal_id = fields.Many2one(
        'account.journal', required=True, ondelete='cascade', domain="[('id', 'in', suitable_journal_ids)]",
        store=True, compute='_compute_journal', readonly=False)
    suitable_journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_suitable_journal_ids',
    )

    @api.depends('move_id')
    @api.depends_context('allowed_company_ids')
    def _compute_company_ids(self):
        self.company_ids = self.env.companies - self.move_id.company_id

    @api.depends('company_ids')
    def _compute_company(self):
        for rec in self:
            rec.company_id = self.company_ids[:1]

    @api.depends('suitable_journal_ids')
    def _compute_journal(self):
        for rec in self:
            rec.journal_id = rec.suitable_journal_ids[:1]

    @api.depends('move_id', 'company_id')
    def _compute_suitable_journal_ids(self):
        """
        We override this method to add filter by companies in the env instead of the company of the user
        For this to work the pr is needed https://github.com/odoo/odoo/pull
        """
        for rec in self:
            journal_type = rec.move_id.invoice_filter_type_domain or 'general'
            domain = [('company_id', '=', rec.company_id._origin.id), ('type', '=', journal_type)]
            rec.suitable_journal_ids = self.env['account.journal'].search(domain)

    def change_company(self):
        self.ensure_one()
        old_name = False
        original_payment_term = False
        # odoo no permite modificar diario si hay name, esto no es del todo correcto para facturas de proveedor con manual number y de hecho deberiamos
        # ver de cambiarlo en el codigo original, por ahora lo permitimos desde aca haciendo backup del nro y restaurando si corresponde
        if self.move_id._fields.get('l10n_latam_manual_document_number') and self.move_id.l10n_latam_manual_document_number and self.move_id.name:
            old_name = self.move_id.name
            self.move_id.name = '/'
        old_doc_type = False
        if self.move_id._fields.get('l10n_latam_document_type_id') and self.move_id.l10n_latam_manual_document_number:
            old_doc_type = self.move_id.l10n_latam_document_type_id

        self.move_id.invoice_line_ids.tax_ids = False
        # si el payment term tiene compañía y es distinta a la que elegimos, forzamos recomputo
        if self.move_id.invoice_payment_term_id.company_id and self.move_id.invoice_payment_term_id.company_id != self.company_id:
            # lo tenemos que hacer antes del write sino se obtiene mensaje "Operación no válida. Empresas incompatibles con los registros"
            self.move_id.with_company(self.move_id.company_id)._compute_invoice_payment_term_id()
        elif not self.move_id.invoice_payment_term_id.company_id:
            original_payment_term = self.move_id.invoice_payment_term_id
            self.move_id.invoice_payment_term_id = False
        invoice_payment_term_id = False
        if self.move_id.is_purchase_document() and self.move_id._origin.partner_id and (not self.move_id.invoice_payment_term_id.company_id or self.move_id.invoice_payment_term_id.company_id == self.move_id.company_id):
            # esto lo hacemos porque sino el write borra el invoice_payment_term_id en facturas de proveedor si en invoice_payment_term_id no tiene compañía
            invoice_payment_term_id = self.move_id.invoice_payment_term_id
        self.move_id.write({
            'company_id': self.company_id.id,
            'journal_id': self.journal_id.id,
        })
        if invoice_payment_term_id:
            self.move_id.invoice_payment_term_id = invoice_payment_term_id
        without_product = self.move_id.line_ids.filtered(lambda line : line.display_type == 'product' and not line.product_id)
        (self.move_id.line_ids - without_product).with_company(self.company_id.id)._compute_account_id()
        for line in without_product:
            line.account_id = line.move_id.journal_id.default_account_id
        if original_payment_term:
            self.move_id.invoice_payment_term_id = original_payment_term.id
        self.move_id.line_ids.with_company(self.company_id.id)._compute_tax_ids()
        self.move_id._compute_partner_bank_id()

        for invoice_line in self.move_id.invoice_line_ids.filtered(lambda x: not x.product_id).with_company(self.company_id.id):
            invoice_line.tax_ids = invoice_line._get_computed_taxes()
        if old_doc_type and old_doc_type in self.move_id.l10n_latam_available_document_type_ids:
            self.move_id.l10n_latam_document_type_id = old_doc_type
            if self.move_id.l10n_latam_manual_document_number:
                self.move_id.name = old_name
