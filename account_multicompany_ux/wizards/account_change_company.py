from odoo import api, fields, models


class AccountChangeCompany(models.TransientModel):
    _name = "account.change.company"
    _description = "Change Company"

    @api.model
    def get_move(self):
        move = self.env["account.move"].browse(self.env.context.get("active_id", False))
        return move

    move_id = fields.Many2one("account.move", default=get_move)
    company_ids = fields.Many2many(
        "res.company",
        string="Companies",
        compute="_compute_company_ids",
    )
    company_id = fields.Many2one(
        "res.company", required=True, ondelete="cascade", compute="_compute_company", store=True, readonly=False
    )
    journal_id = fields.Many2one(
        "account.journal",
        required=True,
        ondelete="cascade",
        domain="[('id', 'in', suitable_journal_ids)]",
        store=True,
        compute="_compute_journal",
        readonly=False,
        check_company=True,
    )
    suitable_journal_ids = fields.Many2many(
        "account.journal",
        compute="_compute_suitable_journal_ids",
    )

    @api.depends("move_id")
    @api.depends_context("allowed_company_ids")
    def _compute_company_ids(self):
        company = self.move_id.company_id
        if not company:
            self.company_ids = self.env["res.company"]
            return
        self.company_ids = company.root_id._accessible_branches() - company

    @api.depends("company_ids")
    def _compute_company(self):
        for rec in self:
            rec.company_id = self.company_ids[:1]

    @api.depends("suitable_journal_ids")
    def _compute_journal(self):
        for rec in self:
            rec.journal_id = rec.suitable_journal_ids[:1]

    @api.depends("move_id", "company_id")
    def _compute_suitable_journal_ids(self):
        """
        We override this method to add filter by companies in the env instead of the company of the user
        For this to work the pr is needed https://github.com/odoo/odoo/pull
        Use _check_company_domain (check_company_domain_parent_of) so that journals from a parent
        company that are shared to branches are also included, not just journals owned directly by
        the selected (branch) company.
        """
        for rec in self:
            journal_type = rec.move_id.invoice_filter_type_domain or "general"
            company = rec.company_id._origin or self.env.company
            domain = [
                *self.env["account.journal"]._check_company_domain(company),
                ("type", "=", journal_type),
            ]
            rec.suitable_journal_ids = self.env["account.journal"].search(domain)

    def change_company(self):
        self.ensure_one()
<<<<<<< 9f6cd3a2eebc43d0a2a23d392ea838c2f7db1293
        old_payment_term = self.move_id.invoice_payment_term_id
        old_fiscal_position = self.move_id.fiscal_position_id
        vals = {
            "company_id": self.company_id.id,
            "journal_id": self.journal_id.id,
||||||| e0dc004b4f9338c2a71c99c1454a2115fc721d28

        # Validar que la empresa destino tenga la misma localización fiscal,
        # salvo que se indique explícitamente que se permite cross-localization.
        if not self.env.context.get("allow_cross_localization", False):
            src_country = self.move_id.company_id.account_fiscal_country_id
            dst_country = self.company_id.account_fiscal_country_id
            if src_country != dst_country and not tools.config["test_enable"]:
                raise UserError(
                    _(
                        "Cannot change company to '%(company)s': it belongs to a different fiscal "
                        "localization (%(dst)s) than the current company (%(src)s). "
                        "Use the context key 'allow_cross_localization' to bypass this restriction."
                    )
                    % {
                        "company": self.company_id.name,
                        "dst": dst_country.name or _("undefined"),
                        "src": src_country.name or _("undefined"),
                    }
                )

        # BACK UP DE DATOS ANTES DE CHANGE DE COMPANY
        old_name = False
        original_payment_term = False
        # odoo no permite modificar diario si hay name, esto no es del todo correcto para facturas de proveedor con manual number y de hecho deberiamos
        # ver de cambiarlo en el codigo original, por ahora lo permitimos desde aca haciendo backup del nro y restaurando si corresponde
        if (
            self.move_id._fields.get("l10n_latam_manual_document_number")
            and self.move_id.l10n_latam_manual_document_number
            and self.move_id.name
        ):
            old_name = self.move_id.name
            self.move_id.name = "/"
        old_doc_type = False
        if self.move_id._fields.get("l10n_latam_document_type_id") and self.move_id.l10n_latam_manual_document_number:
            old_doc_type = self.move_id.l10n_latam_document_type_id

        # BACKUP PARTNER BANK ID
        original_partner_bank_id = self.move_id.partner_bank_id or False

        if self.move_id.fiscal_position_id._fields.get("l10n_ar_tax_ids"):
            fp_tax_group_ids = set(
                self.move_id.fiscal_position_id.l10n_ar_tax_ids.filtered(lambda x: x.tax_type == "perception")
                .mapped("default_tax_id.tax_group_id")
                .ids
            )
        else:
            fp_tax_group_ids = set()
        original_taxes = {
            line.id: [tax.id for tax in line.tax_ids if tax.tax_group_id.id not in fp_tax_group_ids]
            for line in self.move_id.invoice_line_ids
=======

        # Validar que la empresa destino tenga la misma localización fiscal,
        # salvo que se indique explícitamente que se permite cross-localization.
        if not self.env.context.get("allow_cross_localization", False):
            src_country = self.move_id.company_id.account_fiscal_country_id
            dst_country = self.company_id.account_fiscal_country_id
            if src_country != dst_country and not tools.config["test_enable"]:
                raise UserError(
                    _(
                        "Cannot change company to '%(company)s': it belongs to a different fiscal "
                        "localization (%(dst)s) than the current company (%(src)s). "
                        "Use the context key 'allow_cross_localization' to bypass this restriction."
                    )
                    % {
                        "company": self.company_id.name,
                        "dst": dst_country.name or _("undefined"),
                        "src": src_country.name or _("undefined"),
                    }
                )

        # BACK UP DE DATOS ANTES DE CHANGE DE COMPANY
        old_name = False
        original_payment_term = False
        # odoo no permite modificar diario si hay name, esto no es del todo correcto para facturas de proveedor con manual number y de hecho deberiamos
        # ver de cambiarlo en el codigo original, por ahora lo permitimos desde aca haciendo backup del nro y restaurando si corresponde
        if (
            self.move_id._fields.get("l10n_latam_manual_document_number")
            and self.move_id.l10n_latam_manual_document_number
            and self.move_id.name
        ):
            old_name = self.move_id.name
            self.move_id.name = "/"
        old_doc_type = False
        if self.move_id._fields.get("l10n_latam_document_type_id") and self.move_id.l10n_latam_manual_document_number:
            old_doc_type = self.move_id.l10n_latam_document_type_id

        # BACKUP PARTNER BANK ID
        original_partner_bank_id = self.move_id.partner_bank_id or False

        if self.move_id.fiscal_position_id._fields.get("l10n_ar_tax_ids"):
            fp_tax_group_ids = set(
                self.move_id.fiscal_position_id.l10n_ar_tax_ids.filtered(lambda x: x.tax_type == "perception")
                .mapped("default_tax_id.tax_group_id")
                .ids
            )
        else:
            fp_tax_group_ids = set()
        original_taxes = {
            line.id: [tax.id for tax in line.tax_ids if tax.tax_group_id.id not in fp_tax_group_ids]
            for line in self.move_id.invoice_line_ids.filtered(lambda line: line.display_type == "product")
>>>>>>> d5b36eb8d88a5df6530aba3d62964e404346979b
        }
        if old_payment_term and (not old_payment_term.company_id or old_payment_term.company_id == self.company_id):
            vals["invoice_payment_term_id"] = old_payment_term.id
        self.move_id.with_context(skip_invoice_sync=True).write(vals)
        self.move_id.line_ids._compute_account_id() if self.move_id.line_ids else None
        if (
            self.move_id.state == "draft"
            and self.move_id.is_sale_document(include_receipts=True)
            and self.move_id.fiscal_position_id != old_fiscal_position
        ):
            # the write recomputes the fiscal position but not tax_ids, so we call the same method as the
            # "Update Taxes" button. Only if the fiscal position changed: it recomputes taxes from the
            # product, discarding the ones set by hand.
            self.move_id.action_update_fpos_values()
