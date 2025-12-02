from odoo import models
from odoo.fields import Domain
from odoo.tools.misc import unquote


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _check_company_domain(self, companies) -> Domain:
        """
        Override to allow using journals and other resources from parent companies
        when they are marked as shared_to_branches.

        This method adapts the check_company behavior for sale order types to support
        multicompany environments with parent-child relationships, particularly for
        journal_id fields. Allows bidirectional access between parent and child companies.
        """
        if isinstance(companies, unquote):
            companies = unquote(f"{companies}")
        else:
            companies = models.to_record_ids(companies)
        domain = Domain("company_id", "in", companies)
        domain_parent = Domain([("company_id", "parent_of", companies), ("shared_to_branches", "=", True)])
        domain_branches = Domain(
            [
                "|",
                domain_parent,
                ("company_id", "child_of", companies),
            ]
        )
        domain = domain | domain_branches
        return domain
