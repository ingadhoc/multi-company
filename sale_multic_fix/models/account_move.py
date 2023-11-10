# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """ when changing company, we prefer to keep original terms just in case they where modified manually on SO / or invoice"""
        original_narration = self._origin.narration
        super(AccountMove, self)._onchange_partner_id()
        if original_narration and original_narration != self.narration:
            self.narration = original_narration
