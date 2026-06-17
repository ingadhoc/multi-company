##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from collections import defaultdict

from odoo import _, api, fields, models, tools
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
        move_company = self.move_id.company_id
        allow_cross = self.env.context.get("allow_cross_localization", False)
        self.company_ids = (
            self.env.companies.filtered(
                lambda x: (
                    not x.consolidation_company
                    and (allow_cross or x.account_fiscal_country_id == move_company.account_fiscal_country_id)
                )
            )
            - move_company
        )

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
            domain = [
                ("company_id", "=", rec.company_id._origin.id),
                ("type", "=", journal_type),
                ("company_id.consolidation_company", "=", False),
            ]
            rec.suitable_journal_ids = self.env["account.journal"].search(domain)

    def change_company(self):
        self.ensure_one()

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
        }

        # Remove taxes from invoice lines to allow changing account
        # Usamos skip_invoice_sync en TODAS las operaciones sobre líneas para evitar que cada
        # asignación individual (account_id, tax_ids, etc.) dispare _sync_dynamic_lines del move.
        # La sincronización ocurre una sola vez al final, fuera de este contexto.
        move = self.move_id

        # Backup del tax_id de las sale.order.line de anticipo ANTES de modificar la factura.
        # El proceso del wizard dispara el recompute de _compute_tax_id sobre estas líneas, que
        # colapsa todas al impuesto único del producto de anticipo (perdiendo alícuotas múltiples,
        # p.ej. una OV con 21% + 10.5% queda con solo 21% y la factura final no puede cerrarse).
        # La OV no cambia de compañía → los impuestos originales de cada línea siguen siendo válidos.
        dp_sale_lines = move.invoice_line_ids.sale_line_ids.filtered(lambda l: l.is_downpayment and not l.display_type)
        original_dp_sale_taxes = {sol.id: sol.tax_id.ids[:] for sol in dp_sale_lines}

        move.invoice_line_ids.tax_ids = False

        # si el payment term tiene compañía y es distinta a la que elegimos, forzamos recomputo
        if move.invoice_payment_term_id.company_id and move.invoice_payment_term_id.company_id != self.company_id:
            # lo tenemos que hacer antes del write sino se obtiene mensaje "Operación no válida. Empresas incompatibles con los registros"
            move.with_company(move.company_id)._compute_invoice_payment_term_id()
        elif not move.invoice_payment_term_id.company_id:
            original_payment_term = move.invoice_payment_term_id
            move.invoice_payment_term_id = False
        invoice_payment_term_id = False
        if (
            move.is_purchase_document()
            and move._origin.partner_id
            and (
                not move.invoice_payment_term_id.company_id
                or move.invoice_payment_term_id.company_id == move.company_id
            )
        ):
            # esto lo hacemos porque sino el write borra el invoice_payment_term_id en facturas de proveedor si en invoice_payment_term_id no tiene compañía
            invoice_payment_term_id = move.invoice_payment_term_id

        # EMPEZAMOS CON CAMBIOS
        # COMPANY, JOURNAL, DOC TYPE and PAYMENT TERM
        move.with_context(skip_invoice_sync=True).write(
            {
                "partner_bank_id": False,
                "company_id": self.company_id.id,
                "journal_id": self.journal_id.id,
            }
        )

        # LINES ACCOUNTS.
        # tomamos la del producto, o del diario sin no hay producto (salvo para downpamyent que se usan una especificas)
        without_product = move.line_ids.filtered(lambda line: line.display_type == "product" and not line.product_id)
        downpayment_lines = self.env["account.move.line"]
        if move.invoice_line_ids._fields.get("is_downpayment"):
            downpayment_lines = move.invoice_line_ids.filtered(
                lambda x: x.is_downpayment and x.display_type not in ("line_section", "line_note")
            )
        (move.line_ids - without_product - downpayment_lines).with_company(self.company_id.id).with_context(
            skip_invoice_sync=True
        )._compute_account_id()
        default_account = move.journal_id.default_account_id
        (without_product - downpayment_lines).account_id = default_account

        for line in downpayment_lines:
            # TODO podria darse que tengo distintas cuentas para distantas categorias y distintos impuestos
            # tome la cuenta del ultimo producto que encontro.
            # la unica form de correguirlo borrar y calcular las lineas de anticipo pero no sabria igualmente sobre que lineas
            # de la venta calcular el anticipo, ya que la sale order ya podria previamente asociado otro anticipo.
            line.account_id = self._get_change_downpayment_account(self.company_id, line, move.fiscal_position_id)

        # Sincronizar balances con amount_currency antes de cualquier write
        # que dispare _check_balanced (eg. invoice_payment_term_id)
        container = {"records": move}
        with move._disable_recursion(container, "check_move_validity", default=True, target=False):
            self._sync_lines_balance_from_amount_currency(move)

        # PAYMENT TERM
        payment_term = original_payment_term or invoice_payment_term_id
        move._compute_invoice_payment_term_id()
        if payment_term:
            move.invoice_payment_term_id = payment_term
        # Corregir name
        if old_doc_type and old_doc_type in move.l10n_latam_available_document_type_ids:
            move.l10n_latam_document_type_id = old_doc_type
            if move.l10n_latam_manual_document_number:
                move.name = old_name

        # TAXES
        self._get_change_company_line_taxes(move.invoice_line_ids, original_taxes)
        # para percepciones argentinas re-computamos con su propio método
        if move.fiscal_position_id._fields.get("l10n_ar_tax_ids"):
            move._l10n_ar_recompute_fiscal_position_taxes()

        # PARTNER BANK
        if original_partner_bank_id and original_partner_bank_id.company_id.id in [False, self.company_id.id]:
            move.partner_bank_id = original_partner_bank_id

        container = {"records": self.move_id}
        with self.move_id._check_balanced(container), self.move_id._sync_dynamic_lines(container):
            pass

        # Restaurar tax_id de las sale.order.line de anticipo.
        # El _sync_dynamic_lines de arriba (y las operaciones previas del wizard) disparan el
        # recompute de _compute_tax_id que colapsa todas las líneas al impuesto único del producto
        # de anticipo. Restauramos los valores originales por línea para preservar alícuotas múltiples.
        for sol in dp_sale_lines:
            taxes_to_restore = original_dp_sale_taxes.get(sol.id)
            if taxes_to_restore is not None:
                sol.tax_id = [(6, 0, taxes_to_restore)]

    def _sync_lines_balance_from_amount_currency(self, move):
        """Alinea balance con amount_currency para soportar cambio de compañía entre monedas."""
        for line in move.line_ids:
            rate = abs(line.amount_currency / line.balance) if line.balance else 1
            if line.currency_id == line.company_id.currency_id and line.balance != line.amount_currency:
                line.balance = line.amount_currency
            elif (
                line.currency_id != line.company_id.currency_id
                and not self.env.is_protected(line._fields["balance"], line)
                and not line.currency_id.is_zero(rate - line.currency_rate)
            ):
                line.balance = line.company_id.currency_id.round(line.amount_currency / line.currency_rate)

    def _get_change_company_line_taxes(self, lines, taxes):
        """Map taxes from one company to another for invoice or sale order lines.

        Compatible with both account.move.line and sale.order.line.
        """
        by_pass_exception = self.env.context.get("by_pass_exception", False)
        # Ensure lines is a recordset
        if not lines:
            return

        # 1) Recolectar todos los tax IDs únicos de todas las líneas
        all_tax_ids = set()
        for line_tax_ids in taxes.values():
            all_tax_ids.update(line_tax_ids)

        # 2) Buscar el equivalente en la nueva compañía una sola vez por impuesto único
        tax_mapping = {}
        for tax in self.env["account.tax"].browse(list(all_tax_ids)):
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
            if not new_tax and not by_pass_exception:
                message = _(
                    "The selected company (%s) does not have an equivalent tax to '%s' (same type, group and amount)."
                ) % (self.company_id.name, tax.name)
                raise UserError(message)
            tax_mapping[tax.id] = new_tax.id

        # Determine tax field based on the lines we're working with
        # account.move.line uses 'tax_ids', sale.order.line uses 'tax_id' (Many2many in both cases)
        tax_field = None
        if "tax_ids" in lines._fields:
            tax_field = "tax_ids"
        elif "tax_id" in lines._fields:
            tax_field = "tax_id"
        else:
            raise UserError(_("Lines do not have a tax field (tax_ids or tax_id)."))

        # 3) Agrupar líneas por combinación de impuestos originales para hacer writes en lote
        # Create empty recordset of the same model as lines
        lines_by_taxes = defaultdict(lambda: lines.browse())
        for line in lines:
            if line.id in taxes:
                key = tuple(sorted(taxes[line.id]))
                lines_by_taxes[key] |= line

        # 4) Apply tax mapping to each group
        for old_tax_ids, group_lines in lines_by_taxes.items():
            new_tax_ids = [tax_mapping[tid] for tid in old_tax_ids]
            group_lines[tax_field] = [(6, 0, new_tax_ids)]

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
