##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class AccountReport(models.Model):
    _inherit = "account.report"

    def _expand_unfoldable_line(
        self,
        expand_function_name,
        line_dict_id,
        groupby,
        options,
        progress,
        offset,
        horizontal_split_side,
        unfold_all_batch_data=None,
    ):
        """Agregamos sufijo de compañía en reportes financieros si hay más de una compañía seleccionada en el método _compute_display_name de account.account pero necesitamos agregar por contexto el id del reporte porque si no lo hacemos al momento de hacer un unfold de algún rubro en el reporte las cuentas se muestran sin dicho sufijo. Ver ticket 43453 para ver más info acerca de la funcionalidad que necesitamos."""
        self = self.with_context(report_id=self.id)

        return super()._expand_unfoldable_line(
            expand_function_name,
            line_dict_id,
            groupby,
            options,
            progress,
            offset,
            horizontal_split_side,
            unfold_all_batch_data,
        )
