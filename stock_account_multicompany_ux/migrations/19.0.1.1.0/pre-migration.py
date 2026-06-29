def migrate(cr, version):
    """
    shared_to_branches pasó de ser un Boolean normal (columna boolean) a un campo
    company_dependent (columna jsonb por compañía). Postgres no puede convertir
    automáticamente boolean -> jsonb, así que:

    1. Persistimos en una tabla temporal qué categorías tenían el flag en True.
    2. Eliminamos la columna boolean para que Odoo la recree como jsonb al cargar
       el campo company_dependent.
    3. La repoblación con el formato jsonb correcto se hace en post-migration vía
       ORM (que además dispara la sincronización a las branches).
    """
    cr.execute(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'product_category'
          AND column_name = 'shared_to_branches'
        """
    )
    res = cr.fetchone()
    # Si la columna no existe o ya es jsonb, no hay nada que migrar.
    if not res or res[0] == 'jsonb':
        return

    # Guardar las categorías que estaban compartidas (valor global booleano).
    cr.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_account_mc_ux_shared_migr (
            categ_id integer PRIMARY KEY
        )
        """
    )
    cr.execute(
        """
        INSERT INTO stock_account_mc_ux_shared_migr (categ_id)
        SELECT id FROM product_category WHERE shared_to_branches = TRUE
        ON CONFLICT DO NOTHING
        """
    )

    # Eliminar la columna boolean; Odoo recrea shared_to_branches como jsonb.
    cr.execute('ALTER TABLE product_category DROP COLUMN shared_to_branches')
