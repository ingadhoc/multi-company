##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models
from odoo.tools.misc import unquote


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _check_company_domain(self, companies):
        """Override the fallback domain for partner M2O fields with check_company=True.

        Odoo's default behavior generates this expression for the frontend:
            (company_id and [proper_domain] or [('company_id', '=', False)])

        When ``company_id`` is 0/False on the form (new record or field not
        loaded), the ternary collapses to ``[('company_id', '=', False)]``,
        hiding partners that belong to a parent/ancestor company.

        This override replaces the fallback with:
            ['|', ('company_id', '=', False),
                  ('company_id', 'parent_of', context.get('allowed_company_ids', []))]

        So even when ``company_id`` is unset in the form, partners from ancestor
        companies (e.g. the parent company of the active branch) remain visible.

        The fix only applies to the special empty-string sentinel value
        (``companies == ''``) that ``_description_domain`` passes when building
        the no-company fallback clause.  All other callers (record validation,
        Python search, etc.) use non-empty values and are unaffected.
        """
        if companies == "":
            # Build the fallback domain with a context-based expression so the
            # frontend evaluates allowed_company_ids at runtime (not at view-cache time).
            cids = unquote("context.get('allowed_company_ids', [])")
            return ["|", ("company_id", "=", False), ("company_id", "parent_of", cids)]
        return super()._check_company_domain(companies)
