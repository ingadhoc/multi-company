# -*- coding: utf-8 -*-
from odoo import models


class BaseModel(models.AbstractModel):
    _inherit = 'base'
    
    def web_read(self, specification):
        """ Esto lo agregamos para propagar el contexto del active_id """
        fields_to_read = set(specification) or {'id'}
        if hasattr(self, '_property_fields'):
            fields_to_add_context = self._property_fields.intersection(fields_to_read)
            for field in fields_to_add_context:
                specification[field]['context'].update({'active_id':self._ids})
        return super().web_read(specification)
