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
        old_payment_term = self.move_id.invoice_payment_term_id
        old_fiscal_position = self.move_id.fiscal_position_id
        vals = {
            "company_id": self.company_id.id,
            "journal_id": self.journal_id.id,
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
<<<<<<< 708d4eed0c65963ccdf9d90a29614d1926955a22
            # the write recomputes the fiscal position but not tax_ids, so we call the same method as the
            # "Update Taxes" button. Only if the fiscal position changed: it recomputes taxes from the
            # product, discarding the ones set by hand.
            self.move_id.action_update_fpos_values()
||||||| f48789093c52c709c5b492b37ace633fc33bad91
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

        # PARTNER BANK
        if original_partner_bank_id and original_partner_bank_id.company_id.id in [False, self.company_id.id]:
            move.partner_bank_id = original_partner_bank_id

        container = {"records": self.move_id}
        with self.move_id._check_balanced(container), self.move_id._sync_dynamic_lines(container):
            # Percepciones argentinas: re-computamos DENTRO del bloque de sync.
            # _sync_tax_lines toma un snapshot de los tax_ids de las líneas al entrar y solo
            # recomputa (crea el apunte contable) las líneas que cambian dentro de este bloque.
            # Si el recompute corriera antes del bloque, el snapshot ya vería las percepciones
            # puestas y no se generaría el apunte (ticket 122289).
            # Lo hacemos con skip_invoice_sync para que cada asignación de tax_ids no dispare un
            # sync intermedio: un único sync (el de este bloque) reconcilia todas las líneas de una,
            # evitando el O(N²) que agotaba memoria en facturas largas (ingadhoc/multi-company#301).
            if move.fiscal_position_id._fields.get("l10n_ar_tax_ids"):
                move.with_context(skip_invoice_sync=True)._l10n_ar_recompute_fiscal_position_taxes()

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
=======
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

        # PARTNER BANK
        if original_partner_bank_id and original_partner_bank_id.company_id.id in [False, self.company_id.id]:
            move.partner_bank_id = original_partner_bank_id

        container = {"records": self.move_id}
        with self.move_id._check_balanced(container), self.move_id._sync_dynamic_lines(container):
            # Percepciones argentinas: re-computamos DENTRO del bloque de sync.
            # _sync_tax_lines toma un snapshot de los tax_ids de las líneas al entrar y solo
            # recomputa (crea el apunte contable) las líneas que cambian dentro de este bloque.
            # Si el recompute corriera antes del bloque, el snapshot ya vería las percepciones
            # puestas y no se generaría el apunte (ticket 122289).
            # Lo hacemos con skip_invoice_sync para que cada asignación de tax_ids no dispare un
            # sync intermedio: un único sync (el de este bloque) reconcilia todas las líneas de una,
            # evitando el O(N²) que agotaba memoria en facturas largas (ingadhoc/multi-company#301).
            if move.fiscal_position_id._fields.get("l10n_ar_tax_ids"):
                move.with_context(skip_invoice_sync=True)._l10n_ar_recompute_fiscal_position_taxes()

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
            account = product.product_tmpl_id._get_downpayment_or_income_account(line.move_id.company_id, fiscal_pos)
            if account:
                product_accounts.append((product, account))
        if product_accounts:
            matching = [(product, acc) for product, acc in product_accounts if acc == line.account_id]

            if matching:
                matched_product = matching[0][0]
                account = matched_product.product_tmpl_id._get_downpayment_or_income_account(to_company, fiscal_pos)

        if not account:
            line.with_company(to_company.id)._compute_account_id()
            account = line.account_id
        return account
>>>>>>> 71ee8d2a6f0cec29eb687f5521a82e7bf8bff9dc
