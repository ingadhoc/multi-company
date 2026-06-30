##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountReport(models.Model):
    _inherit = "account.report"

    @api.readonly
    def get_options(self, previous_options):
        """Recuperar el reporte cuando se pierde el ``report_id`` del contexto.

        Cuando un reporte se abre desde una declaración (``account.return``) y
        luego se cambia la selección de compañías con el reporte abierto, el
        switch global de compañías dispara una recarga completa de página. Al
        restaurar la acción cliente, el framework reconstruye el contexto como
        ``{'active_id': <return_id>}`` y descarta el ``report_id``, por lo que
        este método se ejecuta sobre un recordset vacío y ``ensure_one()``
        revienta con ``Expected singleton: account.report()``. Recuperamos el
        reporte desde la declaración apuntada por ``active_id``. Ver ticket
        121344.

        Solo recuperamos si el ``active_model`` está ausente (caso del bug, donde
        el framework deja el contexto en ``{'active_id'}``) o es explícitamente
        ``account.return``; así evitamos resolver un ``account.return`` por
        casualidad cuando ``active_id`` pertenece a otro modelo con id solapado.

        El chequeo ``"account.return" in self.env`` cubre instalaciones donde ese
        modelo no esté disponible: en ese caso degradamos al comportamiento de
        ``super()`` (el ``ensure_one()`` original) en vez de romper con KeyError.
        """
        if not self and "account.return" in self.env:
            active_id = self.env.context.get("active_id")
            active_model = self.env.context.get("active_model")
            if active_id and active_model in (None, False, "account.return"):
                account_return = self.env["account.return"].browse(active_id).exists()
                if account_return.type_id.report_id:
                    self = account_return.type_id.report_id
        return super().get_options(previous_options)

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
        """Agregamos sufijo de compañía en reportes financieros si hay más de
        una compañía seleccionada en el método _compute_display_name de
        account.account pero necesitamos agregar por contexto el id del reporte
        porque si no lo hacemos al momento de hacer un unfold de algún rubro
        en el reporte las cuentas se muestran sin dicho sufijo. Ver ticket
        43453 para ver más info acerca de la funcionalidad que necesitamos.
        """
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
