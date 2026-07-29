def migrate(cr, version):
    """
    Saca la lectura de las reglas multicompañía de stock, que pasa a gobernar este
    módulo. Están declaradas con noupdate="1", así que el XML solo las toca al
    instalar: en una base ya instalada hay que forzarlo acá.
    """
    cr.execute(
        """
        UPDATE ir_rule SET perm_read = FALSE
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE model = 'ir.rule'
              AND module = 'stock'
              AND name IN ('stock_location_comp_rule', 'stock_quant_rule')
        )
        """
    )
