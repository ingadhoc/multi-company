##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountChangeCurrency(models.TransientModel):
    _name = "account.change.company"
    _description = "Change Company"

    @api.model
    def get_move(self):
        move = self.env["account.move"].browse(self._context.get("active_id", False))
        return move

    move_id = fields.Many2one("account.move", default=get_move)
    company_ids = fields.Many2many("res.company", string="Companies", compute="_compute_company_ids")
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
    )
    suitable_journal_ids = fields.Many2many(
        "account.journal",
        compute="_compute_suitable_journal_ids",
    )

    @api.depends("move_id")
    @api.depends_context("allowed_company_ids")
    def _compute_company_ids(self):
        self.company_ids = self.env.companies - self.move_id.company_id

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
        """
        for rec in self:
            journal_type = rec.move_id.invoice_filter_type_domain or "general"
            domain = [("company_id", "=", rec.company_id._origin.id), ("type", "=", journal_type)]
            rec.suitable_journal_ids = self.env["account.journal"].search(domain)

    def change_company(self):
        self.ensure_one()

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

        # backup de original taxes
        if self.move_id.fiscal_position_id._fields.get("l10n_ar_tax_ids"):
            fp_tax_groups = self.move_id.fiscal_position_id.l10n_ar_tax_ids.filtered(
                lambda x: x.tax_type == "perception"
            ).mapped("default_tax_id.tax_group_id")
        else:
            fp_tax_groups = self.env["account.tax.group"]
        original_taxes = {
            line.id: line.tax_ids.filtered(lambda x: x.tax_group_id not in fp_tax_groups).ids[:]
            for line in self.move_id.invoice_line_ids
        }

        # Remove taxes from invoice lines to allow changing account
        self.move_id.invoice_line_ids.tax_ids = False

        # si el payment term tiene compañía y es distinta a la que elegimos, forzamos recomputo
        if (
            self.move_id.invoice_payment_term_id.company_id
            and self.move_id.invoice_payment_term_id.company_id != self.company_id
        ):
            # lo tenemos que hacer antes del write sino se obtiene mensaje "Operación no válida. Empresas incompatibles con los registros"
            self.move_id.with_company(self.move_id.company_id)._compute_invoice_payment_term_id()
        elif not self.move_id.invoice_payment_term_id.company_id:
            original_payment_term = self.move_id.invoice_payment_term_id
            self.move_id.invoice_payment_term_id = False
        invoice_payment_term_id = False
        if (
            self.move_id.is_purchase_document()
            and self.move_id._origin.partner_id
            and (
                not self.move_id.invoice_payment_term_id.company_id
                or self.move_id.invoice_payment_term_id.company_id == self.move_id.company_id
            )
        ):
            # esto lo hacemos porque sino el write borra el invoice_payment_term_id en facturas de proveedor si en invoice_payment_term_id no tiene compañía
            invoice_payment_term_id = self.move_id.invoice_payment_term_id

        # EMPEZAMOS CON CAMBIOS
        # COMPANY, JOURNAL, DOC TYPE and PAYMENT TERM
        self.move_id.with_context(skip_invoice_sync=True).write(
            {
                "partner_bank_id": False,
                "company_id": self.company_id.id,
                "journal_id": self.journal_id.id,
            }
        )

        # LINES ACCOUNTS.
        # tomamos la del producto, o del diario sin no hay producto (salvo para downpamyent que se usan una especificas)
        without_product = self.move_id.line_ids.filtered(
            lambda line: line.display_type == "product" and not line.product_id
        )
        downpayment_lines = self.env["account.move.line"]
        if self.move_id.invoice_line_ids._fields.get("is_downpayment"):
            downpayment_lines = self.move_id.invoice_line_ids.filtered("is_downpayment")
        (self.move_id.line_ids - without_product - downpayment_lines).with_company(
            self.company_id.id
        )._compute_account_id()
        for line in without_product - downpayment_lines:
            line.account_id = line.move_id.journal_id.default_account_id

        for line in downpayment_lines:
            # TODO podria darse que tengo distintas cuentas para distantas categorias y distintos impuestos
            # tome la cuenta del ultimo producto que encontro.
            # la unica form de correguirlo borrar y calcular las lineas de anticipo pero no sabria igualmente sobre que lineas
            # de la venta calcular el anticipo, ya que la sale order ya podria previamente asociado otro anticipo.
            line.account_id = self._get_change_downpayment_account(
                self.company_id, line, self.move_id.fiscal_position_id
            )

        # PAYMENT TERM
        if invoice_payment_term_id:
            self.move_id.invoice_payment_term_id = invoice_payment_term_id
        if original_payment_term:
            self.move_id.invoice_payment_term_id = original_payment_term.id

        # Corregir name
        if old_doc_type and old_doc_type in self.move_id.l10n_latam_available_document_type_ids:
            self.move_id.l10n_latam_document_type_id = old_doc_type
            if self.move_id.l10n_latam_manual_document_number:
                self.move_id.name = old_name

        # TAXES
        self._get_change_company_line_taxes(self.move_id.invoice_line_ids, original_taxes)
        # para percepciones argentinas re-computamos con su propio método
        if self.move_id.fiscal_position_id._fields.get("l10n_ar_tax_ids"):
            self.move_id._l10n_ar_recompute_fiscal_position_taxes()

    def _get_change_company_line_taxes(self, lines, taxes):
        """Por ahora a nivel taxes solo usamos el mapping para líneas de descuento y downpayment
        Si duele y todo va bien podemos extenderlo a todas las líneas
        """
        for line in lines:
            tax_ids = self.env["account.tax"].browse(taxes[line.id])
            new_tax_ids = []
            for tax in tax_ids:
                new_tax = self.env["account.tax"].search(
                    [
                        ("type_tax_use", "=", tax.type_tax_use),
                        ("tax_group_id.name", "=", tax.tax_group_id.name),
                        ("amount", "=", tax.amount),
                        ("active", "=", True),
                        ("price_include_override", "=", tax.price_include_override),
                        ("company_id", "=", self.company_id.id),
                    ],
                    limit=1,
                )
                if not new_tax:
                    # TODO adaptar mensaje
                    message = _(
                        "The selected company (%s) does not have an equivalent tax to '%s' "
                        "(same type, group and amount)."
                    ) % (self.company_id.name, tax.name)
                    # a validar si raise o no. El raise nos protege más de no hacer error.
                    raise UserError(message)
                    # self.move_id.message_post(body=message)
                    # continue
                new_tax_ids.append(new_tax.id)
            line.tax_ids = [(6, 0, new_tax_ids)]

    @api.model
    def _get_change_downpayment_account(self, to_company, line, fiscal_pos):
        """Update account_id on lines with the correct downpayment or income account."""
        account = False
        products = line.sale_line_ids.mapped("order_id.order_line.product_id")
        product_accounts = []
        for product in products:
            accounts = product.product_tmpl_id.with_company(line.move_id.company_id).get_product_accounts(
                fiscal_pos=fiscal_pos
            )
            account = accounts.get("downpayment") or accounts.get("income")
            if account:
                product_accounts.append((product, account))
        if product_accounts:
            matching = [(product, acc) for product, acc in product_accounts if acc == line.account_id]

            if matching:
                matched_product = matching[0][0]
                matched_account = matched_product.product_tmpl_id.with_company(to_company).get_product_accounts(
                    fiscal_pos=fiscal_pos
                )
                account = matched_account.get("downpayment") or matched_account.get("income")

        if not account:
            line.with_company(to_company.id)._compute_account_id()
            account = line.account_id
        return account
