# Migración de código: stock_account_multicompany_ux 19.0 → 20.0

## Resumen
Migrado con puntos a revisar: instala en una base 20 y los 17 tests pasan. Quedan dos temas contables para gl (par de diferencia y la 77209) y la conversión de permisos, que se tiene que validar en una base real.
Revisión de cambios liviana: gl (PO) dejó el análisis de impacto del 16/10 con instrucciones por archivo y "se mantiene el comportamiento de 19" (ADR 0046).
Origen posterior a la base común: se trajo `8f6cb01a4` (Weblate, es.po) con `cherry-pick -x`. No hay FW abiertos para cerrar. El arreglo del par de diferencia nace en 19 (`19.0-t-76435-rov`) y se trajo con `cherry-pick -x`: cuando se mezcle en 19, el FW que abra el bot se cierra apuntando a este PR.
actua-20 @ 40e230f

## Automático (migrator y upgrade_code)
- Migrator (fork adhoc, 19.0→20.0): versión `20.0.1.0.0`, `installable: True` y borró `migrations/` (19.0.1.1.0 y 19.0.1.5.0, del salto 18→19). El catálogo respondió.
- upgrade_code: la carpeta de `odoo-20` coincide con odoo/odoo@20.0 (core `b882325ea`, imagen del 2026-11-12). Solo `19.4-00-ir-access` cambió algo: pasó las dos `ir.rule` propias a `security/ir.access.csv`. Las dos escrituras sobre `stock.stock_location_comp_rule` y `stock.stock_quant_rule` las dejó como `ir.rule` (se resolvieron a mano). El resto de los scripts: 0 archivos.

## Resuelto agénticamente
- COGS de la branch (`models/account_move_line.py`): `_get_stock_moves()` → `cogs_move_ids`. Evidencia: 19 `stock_account/models/account_move_line.py:79` → 20 `stock_account/models/account_move_line.py:14` y `sale_stock/models/account_move.py:127`.
- COGS sin moves en FIFO: `_run_fifo(qty)` → `_get_fifo_value(qty)`. Evidencia: 19 `stock_account/models/product.py:538` → 20 `stock_account/models/product.py:618`, usado igual por el estándar en `stock_account/models/account_move_line.py:61`.
- Sin la resta de `_get_posted_cogs_value()`: el estándar de 20 promedia todos los moves de la línea de venta y no resta lo contabilizado. Evidencia: 19 `stock_account/models/account_move_line.py:75` → 20 `stock_account/models/account_move_line.py:57-63`. Se conserva el caso propio de NC (precio de la factura original).
- `stock.move._get_cogs_price_unit`: queda como método propio, sin `super()`, porque en 20 no está (version change 12095). Sin branch ni categoría compartida devuelve `_get_price_unit(include_consigned=True, product=...)`, el mismo precio del estándar (20 `stock_account/models/stock_move.py:330`). Se mantiene el nombre porque `account_invoice_historical_cost` lo sigue llamando en su 20.0 (`origin/20.0:account_invoice_historical_cost/models/account_move_line.py:107`, con `branch_company` en el contexto), como pedía cem el 21/10.
- Costo FIFO/AVCO con lote de la branch: `_get_price_unit(product=...)`, que divide el valor con signo por la cantidad con signo. En 20 el `value` de una salida es negativo y el de una devolución, positivo. Evidencia: 19 `stock_account/models/stock_move.py:285` (salidas positivas) → 20 `stock_account/models/stock_move.py:353,547-551` (`_get_valued_qty(signed=True)`). Un primer arreglo con `abs()` daba mal con devoluciones: lo encontró la revisión adversarial y se corrigió en el commit `[FIX]`.
- Par de diferencia de inventario (`models/account_move.py`): `_stock_account_prepare_realtime_out_lines_vals` → override de `account.move._get_cogs_lines_vals` (20 `account/models/account_move.py:6069`). `_eligible_for_stock_account()` + `valuation == real_time` → `_use_inventory_valuation()` (20 `account/models/account_move_line.py:3847`). Los vals usan `_get_cogs_common_vals` y `balance` (20 `account/models/account_move.py:6052`). `currency_id.is_zero` → `company_currency_id.is_zero`, porque la diferencia está en moneda de la compañía. Con moneda extranjera, en 19 el par en `amount_currency` quedaba mal; en 20 queda en moneda de la compañía, igual que el COGS (lo verificó la revisión adversarial).
- Nuevo override de `account.move.line._set_cogs`: el recálculo retroactivo de 20 (`stock_account/models/account_move_line.py:16`, llamado desde `stock_move.py:195,255`) reescribe todas las líneas cogs de la factura con el valor de los moves de la branch. Pisaba el COGS al costo de la madre y convertía el par de diferencia en otro par de COGS. Las categorías compartidas de una branch quedan como se contabilizaron, igual que en 19 (que no tenía recálculo). Test nuevo `test_set_cogs_keeps_parent_cost`: rojo sin el override, verde con él. Cubre la factura sin moves, porque el módulo no depende de `sale_stock`. El caso real (factura después de la entrega, donde el `_set_cogs` estándar convierte `[DF 160, EX 400, SV -400, SV -160]` en `[DF 240, EX 240, SV -240, SV -240]`) se verificó a mano en la base.
- Valor contable (`models/res_company.py`): `stock_accounting_value(accounts_by_product, at_date)` → `get_inventory_accounting_value(at_date)`, con `_get_accounts_by_product(at_date)`. Evidencia: 20 `account/models/company.py:1431,1478`. La compañía sin madre ni sucursales delega en el estándar.
- Seguridad: `stock.stock_location_comp_rule` y `stock.stock_quant_rule` son `ir.access` en 20 (`stock/security/ir.access.csv:7,33`, operación `crud`, sin grupo, o sea restricciones que se combinan con AND). El módulo les pone `operation = cud` (en 19, `perm_read = False`). `uninstall_hook`: `perm_read = True` → `operation = "crud"`.
- Vistas: la de categoría hereda `account.view_category_property_form` (20 `account/views/product_view.xml:116`). En 19 era `stock_account.view_category_property_form_stock`, que en 20 no existe. La vista sobre `product.product_variant_easy_edit_view` se sacó (ver Bajas).
- Tests: `_get_stock_moves()` → `cogs_move_ids`, `stock_accounting_value` → `get_inventory_accounting_value`.

## Revisión adversarial
Atacó las 8 afirmaciones del porte con escenarios en la base 20 (factura parcial, devoluciones, NC, multimoneda, `_set_cogs` real, factura antes de entregar). Nada de 19 se corrió: lo de 19 es lectura de código.
- ALTA, del salto, **corregido**: el `abs(sum(value))` daba mal el costo de la branch con devoluciones en la línea de venta (25,71 en vez de 60). Ahora va `_get_price_unit`. Repetido: `(100.0, 60.0)`.
- ALTA, preexistente, **corregido desde 19 (pedido de rov, 13/11)**: el par de diferencia usaba la cantidad de todos los moves de la línea de venta, no la de la factura. Arreglo en `19.0-t-76435-rov` (commit `c7fe711`, PR aparte contra 19.0, con el test `test_inventory_cost_difference_uses_given_quantity`: en 19 da rojo sin el arreglo, `-200.0 != 160.0`, y 17/17 ok con él). Traído a 20 con `cherry-pick -x` (`99470c3`). Repetido en 20: factura de 4 sobre entrega de 10 → par 160; segunda factura de 2 → 80; NC de 4 → -160.
- MEDIA, corregido en el reporte: `account_invoice_historical_cost` sigue llamando a `_get_cogs_price_unit` en su 20.0. Por eso el método queda con ese nombre.
- MEDIA, del salto: el test nuevo de `_set_cogs` cubre la factura sin moves; el caso con moves se verificó a mano (ver *Resuelto*).
- INFORMATIVO, preexistente: si se factura antes de entregar no hay par de diferencia (en 19 tampoco).
- INFORMATIVO: la SV de la branch en -560 de la prueba pasaba igual en 19 (leído del código: sin asiento de entrega, COGS y par contra la SV, mismo signo). En 19 el lado SV del par además distorsionaba el COGS de la factura siguiente de la misma línea, vía `_get_posted_cogs_value`; en 20 ya no.
- INFORMATIVO, preexistente: las acumulaciones del reporte de valuación (`sale/wizard/accrued_orders.py:99`) usan el costo de la branch, no el de la madre. Igual en 19.
- BAJA, preexistente: el docstring de `get_inventory_accounting_value` para la madre no coincide con el código (suma todos los AMLs del grupo). La NC, caso 1, filtra `price_unit >= 0` sin mirar la cuenta, y podría tomar la línea de diferencia (sin reproducir).
- De la regla, para el programa: el cambio de signo de `stock.move.value` en las salidas (con `_get_valued_qty(signed=)`) afecta a cualquier módulo que sume `value` mezclando entradas y salidas. El version change 12292 lo muestra como cambio de firma y se leyó "compatible". Conviene un version change de comportamiento.
- check_anclas.py lo corrió el revisor contra `20.0-mig-stock_currency_valuation` (stock_account sin el módulo): 3 anclas, 0 perdidas, 0 sin cubrir, 1 SIN CAMPO falso positivo (`product_stock_by_location.view_template_stock_by_location_form`, que no muestra `standard_price`).
- No verificado: POS (`pos_stock` redefine `_get_cogs_value`), repair, `_get_value_from_previous_company` en cadenas entre compañías, y la división por producto de `stock_account_ux`.

## Bajas
- `campo-vista:product_variant_easy_edit_view_shared_cost:arch` — portado: la vista padre `product.product_variant_easy_edit_view` no existe en 20; el costo de la madre en la variante lo sigue mostrando `product_template_form_view_shared_cost` (views/product_views.xml), porque `product.product_normal_form_view` hereda el formulario de plantilla (`product/views/product_views.xml:512` de 20).
- `campo-vista:product_variant_easy_edit_view_shared_cost:is_cost_shared_from_parent` — portado: la vista padre `product.product_variant_easy_edit_view` no existe en 20; el costo de la madre en la variante lo sigue mostrando `product_template_form_view_shared_cost` (views/product_views.xml), porque `product.product_normal_form_view` hereda el formulario de plantilla (`product/views/product_views.xml:512` de 20).
- `campo-vista:product_variant_easy_edit_view_shared_cost:parent_standard_price` — portado: la vista padre `product.product_variant_easy_edit_view` no existe en 20; el costo de la madre en la variante lo sigue mostrando `product_template_form_view_shared_cost` (views/product_views.xml), porque `product.product_normal_form_view` hereda el formulario de plantilla (`product/views/product_views.xml:512` de 20).
- `registro:product_variant_easy_edit_view_shared_cost` — portado: la vista padre `product.product_variant_easy_edit_view` no existe en 20; el costo de la madre en la variante lo sigue mostrando `product_template_form_view_shared_cost` (views/product_views.xml), porque `product.product_normal_form_view` hereda el formulario de plantilla (`product/views/product_views.xml:512` de 20).
- `metodo:account.move._stock_account_prepare_realtime_out_lines_vals` — portado: `account.move._get_cogs_lines_vals` (`models/account_move.py`).
- `metodo:res.company.stock_accounting_value` — portado: `res.company.get_inventory_accounting_value` (`models/res_company.py`).

## Requiere revisión humana
- **Par de diferencia de inventario en 20 (para gl).** Prueba en la base 20: categoría standard en tiempo real, costo 100 en la madre y 60 en la branch. La branch recibe 10 y vende, entrega y factura 4. La entrega no genera asiento. La factura acredita SV por 400 (COGS al costo de la madre) y el par de diferencia acredita SV por 160 más y debita Diferencia por 160. La SV de la branch queda en -560. El par mueve la cuenta en el mismo sentido que el COGS. Se migró igual que en 19 (el código de 19 ya pedía "validar el signo/cuentas"). No está verificado si en 19 daba lo mismo. rov (13/11): con `shared_to_branches` se usa siempre el costo de la madre. Se deja como está: con el costo unificado la diferencia es 0 y el par no se genera. Solo aparece si el costo de la branch quedó distinto del de la madre.
- **La 77209 sigue abierta.** gl pidió decidir la valorización multicompañía ahí antes de migrar (nota del 22/10). Se migró preservando 19, por pedido de rov (13/11). Lo que se decida puede cambiar este PR.
- **check_permisos da 2 ALERTA** ("baja ... sin r y se lo saca a todo"). Es intencional y equivale a 19: se le saca la lectura a la restricción global de stock y la reemplazan las dos restricciones de lectura propias, más amplias con el privilegio *All Branches*. Necesita el OK de rov.
- Help de campos con msgid en castellano (`parent_standard_price`, `is_cost_shared_from_parent`, `company_has_branches`): vienen de 19 y quedan sin traducir en el `es.po`. Pasarlos a inglés es un cambio aparte.

## Bloqueantes
- Ninguno.

## Migración de data
- ¿Hace falta script? no — respondió rov (13/11), motivo: no cambia ningún dato guardado. `shared_to_branches` no cambia. Las restricciones de stock las vuelve a escribir el `-u` del módulo (no son `noupdate` en 20).
- A validar en base real: que el pase de Odoo convierta a `ir.access` las `ir.rule` propias (`stock_account_multicompany_ux.stock_location_read_rule`, `stock_quant_read_rule`) conservando el xmlid. La nota del version change lo confirma para las 867 estándar, no para las de módulos propios.

## Candidatos a gestión del cambio
- ninguno: se mantiene el comportamiento de 19. Lo que cambia de lugar es la pestaña: el check se ve en *Contabilidad* de la categoría, igual que el resto de la valoración en 20.

## Verificación
- chequeo estático: ok (ruff no disponible en el host: solo sintaxis); imports de JS: 0 revisados (sin JS); precisiones decimales: 0 sin definir; imports de Python (check_imports.py): 9 revisados, ok
- permisos (paso 3b): 2 ALERTA, intencionales (ver *Requiere revisión humana*); xmlid que se van o nuevos: `stock_location_read_rule` y `stock_quant_read_rule` pasan de `ir.rule` a `ir.access` con el mismo xmlid
- anclas de vistas heredadas (paso 3c): en la base de la migración no se pudo correr (el módulo es `auto_install` y se instala solo con sus dependencias). Lo corrió la revisión adversarial contra `20.0-mig-stock_currency_valuation`, sin el módulo: 3 anclas, 0 perdidas, 0 sin cubrir, 1 SIN CAMPO falso positivo (`product_stock_by_location.view_template_stock_by_location_form` no muestra `standard_price`).
- registros de otros módulos (paso 3d): 2 PISA (`stock.stock_location_comp_rule.operation`, `stock.stock_quant_rule.operation` = `cud`) con CAMBIA EN DESTINO. En 19 eran `ir.rule` y no tenían `operation`: es la misma escritura que hacía 19 sobre `perm_read`.
- pre-commit: pasó
- manifest version / installable: `20.0.1.0.0` / True
- intención (pre-flight): MIGRAR — tarea 76435 sin baja, notas de gl (PO) del 16/10 ("se mantiene el comportamiento de 19") y del 27/10 en 77209 ("el core no reemplaza a shared_to_branches") · estado en destino: Migrando
- qué cambió (paso 0): `_get_cogs_price_unit`, `_get_stock_moves`, `_get_posted_cogs_value`, `_eligible_for_stock_account`, `_stock_account_prepare_realtime_out_lines_vals`, `stock_accounting_value`, `_run_fifo` → todos en `models/` (ver *Resuelto*). El digest (2026-09-28) da `_get_cogs_price_unit` → `_get_value_from_previous_company` como rename inferido: no lo es (lo dijo gl el 16/10).
- version changes (paso 0): 11 de métodos listados por check_metodos.py, 11 aplican (resueltos). Quedan 4 después de migrar y no aplican: 12095/12287 (`_get_cogs_price_unit` ahora es método propio, sin super), 12286 (`_get_price_unit` ya se usa con la firma de 20) y 12292 (`_get_valued_qty` sin `signed`, compatible). Del migrator, `ir.rule` (aplica, resuelto) y `property_cost_method` sin fifo (falso positivo según la nota: `stock_account` lo sigue sumando). super() que no resuelven: 0; llamadas de destino que no encajan: 0; parámetros con otro nombre: 0; compute_sql: 0
- wiki funcional (paso 0): no nombra al módulo
- qué espera destino (paso 0b): `account_invoice_historical_cost` (20.0) → `stock.move._get_cogs_price_unit(quantity)` con `branch_company` en el contexto → está
- scripts de `migrations/` (paso 0f): 3 scripts, los 3 de 19.*, 0 DESTINO, 0 TODO
- red de tests (paso 0c): tiene: 16 tests con asserts en 19 (3 archivos)
- tests nuevos para el código de destino: `test_set_cogs_keeps_parent_cost` (el override de `_set_cogs`, nuevo en 20). No es red de regresión. Se sacó `test_accounting_value_respects_accounts_by_product`: el parámetro no existe en 20.
- manifiesto: sin cambios en `depends` ni `auto_install`. `security/ir.access.csv` sumado a `data`.
- licencia (paso 4c): AGPL-3 → AGPL-3, no llega a Enterprise; repo público que llega a Enterprise: no aplica
- base 20 local: instaló; tests del módulo (resumen_tests.py): 17 ok, 0 fallados, 0 salteados, con sale_stock instalado. Además, la prueba a mano del flujo madre/branch con entrega (standard, average, fifo): COGS 400 al costo de la madre y el par de diferencia de 160, iguales después de `_set_cogs`. Capturas: no ofrecidas todavía.
- grupos del usuario del test (paso 4b): no aplica: sin `BaseCommon` ni `Form`
- README (paso 4d): sincronizado a mano con el criterio de odoo-auto-readme (sin reestructurar, en inglés): ganchos de 20, `_set_cogs`, restricciones `ir.access` y la pestaña *Accounting*
- traducciones (paso 4e): exportado con es_po_es419.py; 16 traducidos; 1 tomó la redacción del glosario (Display Name); 3 msgid en castellano sin traducir; descripción del módulo sin traducir, para revisión
- otros: el clon de `ingadhoc-miscellaneous` está en `20.0-t-76423-rov` y el de `ingadhoc-account-financial-tools` en `20.0-t-76380-cav` (no se tocaron). Los tests corrieron con esas ramas. El aviso `union()` del log viene de `stock_account_ux`.
- base real post-ODU: sin base para el par: runbot todavía no corre el salto a 20 (77184)
