from odoo import models


class ResCompanyPropertyMixin(models.AbstractModel):
    _name = "res.company.property.mixin"
    _description = "Company property mixin abstract"

    def web_read(self, specification):
        """Esto lo agregamos para propagar el contexto del active_id"""
        fields_to_read = set(specification) or {"id"}
        if hasattr(self, "_property_fields"):
            fields_to_add_context = self._property_fields.intersection(fields_to_read)
            for field in fields_to_add_context:
                specification[field].setdefault("context", {})
                specification[field]["context"].update({"active_id": self._ids})
        return super().web_read(specification)

    def action_company_properties(self):
        self.ensure_one()
        action = (
            self.env["res.company.property"]
            .with_context(active_model=self._name, active_id=self.id)
            .action_company_properties()
        )
        if self._context.get("property_field") == "property_account_position_id":
            view_id = self.env.ref("account_multicompany_ux.view_property_position_id_form").id
        elif self._context.get("property_field") == "property_payment_term_id":
            view_id = self.env.ref("account_multicompany_ux.view_property_term_id_form").id
        elif self._context.get("property_field") == "property_product_pricelist":
            view_id = self.env.ref("account_multicompany_ux.view_property_pricelist_id_form").id
        elif self._context.get("property_field") == "credit":
            view_id = self.env.ref("account_multicompany_ux.view_property_credit_form").id
        elif self._context.get("property_field") == "property_supplier_payment_term_id":
            view_id = self.env.ref("account_multicompany_ux.view_property_term_id_form").id
        elif self._context.get("property_field").startswith("property_account"):
            view_id = self.env.ref("account_multicompany_ux.view_property_account_id_form").id
        else:
            view_id = self.env.ref("account_multicompany_ux.view_standard_price_form").id
        action["views"] = [[view_id, "list"]]
        return action
