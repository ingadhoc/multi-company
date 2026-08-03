##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, models

# Los dos campos de contabilidad que dejan de delegarse a la compañía raíz.
# El resto de los campos delegados (currency_id, account_storno,
# tax_exigibility) se siguen delegando: acá solo tocamos el ejercicio.
FISCALYEAR_FIELD_NAMES = ("fiscalyear_last_day", "fiscalyear_last_month")


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_company_root_delegated_field_names(self):
        """Saca el ejercicio fiscal de la delegación a la compañía raíz.

        Core delega cinco campos a la raíz y los hace cumplir con cuatro
        mecanismos, los cuatro apoyados en este método: el campo readonly en la
        vista (`_get_view`), la copia en `create`, la propagación a las hijas en
        `write` y el constraint `_check_root_delegated_fields`. Sacar los dos
        campos del ejercicio de la lista levanta los cuatro de una.

        De los cuatro, el único que no queremos perder es la copia en `create`:
        una sucursal nueva tiene que seguir naciendo con el ejercicio de su
        raíz, porque la divergencia es la excepción y no el default. Eso se
        restituye más abajo (`create` y `_onchange_parent_id`).
        """
        return [
            fname for fname in super()._get_company_root_delegated_field_names() if fname not in FISCALYEAR_FIELD_NAMES
        ]

    @api.model_create_multi
    def create(self, vals_list):
        """Restituye la herencia del ejercicio en la creación de una sucursal.

        Solo como valor inicial: después queda editable y no se vuelve a
        propagar (a diferencia de un campo delegado, donde un cambio en la raíz
        pisa a todas las hijas).
        """
        for vals in vals_list:
            if parent := self.browse(vals.get("parent_id")):
                for fname in FISCALYEAR_FIELD_NAMES:
                    vals.setdefault(fname, self._fields[fname].convert_to_write(parent[fname], parent))
        return super().create(vals_list)

    @api.onchange("parent_id")
    def _onchange_parent_id_fiscalyear(self):
        """Idem `create`, pero para el form: al elegir la raíz, el ejercicio se
        propone desde ella. Core lo hacía en `_onchange_parent_id` recorriendo
        los campos delegados, y el ejercicio ya no está en esa lista.

        Hace falta además de `create` porque el cliente web manda todos los
        campos del registro nuevo, así que el `setdefault` de `create` no llega
        a aplicar cuando la sucursal se crea desde la interfaz.
        """
        if self.parent_id:
            for fname in FISCALYEAR_FIELD_NAMES:
                if self[fname] != self.parent_id[fname]:
                    self[fname] = self.parent_id[fname]
