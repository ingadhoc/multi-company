from . import models


def uninstall_hook(env):
    # Sin esto la lectura de stock quedaría sin ninguna regla de compañía.
    for xml_id in ("stock.stock_location_comp_rule", "stock.stock_quant_rule"):
        rule = env.ref(xml_id, raise_if_not_found=False)
        if rule:
            rule.perm_read = True
