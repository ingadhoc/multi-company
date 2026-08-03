.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==========================
Account Branch Fiscal Year
==========================

Permite que las sucursales (*branches*) de un mismo árbol de compañías tengan
un cierre de ejercicio distinto al de la compañía raíz.

Por default Odoo delega cinco campos de la compañía raíz a sus sucursales
(``currency_id``, ``fiscalyear_last_day``, ``fiscalyear_last_month``,
``account_storno`` y ``tax_exigibility``), y los hace cumplir con cuatro
mecanismos: el campo readonly en la vista, la copia en ``create``, la
propagación a las hijas en ``write`` y un constraint de Python. Este módulo
saca **solo los dos campos del ejercicio** de esa lista. El resto de la
delegación —la moneda entre ellos— queda intacta.

Qué hace exactamente
====================

#. El cierre de ejercicio queda **editable** en la ficha de la sucursal.
#. Un cambio de ejercicio en la raíz **ya no pisa** el de sus sucursales.
#. Una sucursal nueva **sigue naciendo con el ejercicio de su raíz**: la
   divergencia es la excepción, no el default. Se restituye la copia en
   ``create`` y en el ``onchange`` de la compañía padre.
#. Lo que resuelve el ejercicio con la compañía del registro pasa a verlo
   bien: amortizaciones, la secuencia por ejercicio de los asientos, el libro
   diario y la valuación continental de stock.

Limitaciones — leer antes de instalarlo
=======================================

**Este módulo levanta la restricción; no arregla todo lo que la restricción
tapaba.** Hay tres lugares donde el ejercicio no se resuelve con la compañía
de la sucursal, y siguen igual con el módulo instalado:

#. **Fechas de bloqueo.** Se resuelven recorriendo la cadena de compañías
   padre y tomando el máximo. Cuando la raíz cierra su ejercicio y pone la
   fecha de bloqueo, **bloquea también a las sucursales**, en medio del
   ejercicio de la sucursal. Los bloqueos blandos admiten excepción por
   usuario (``account.lock_exception``); el bloqueo duro (*hard lock date*)
   no admite ninguna, por diseño.
#. **Corte del resultado del ejercicio en los reportes.** El libro mayor y
   sumas y saldos calculan el inicio del ejercicio **una sola vez, con la
   compañía activa**, y lo aplican a las líneas de todas las compañías
   seleccionadas. Con cierres dispares, el saldo inicial y el resultado de la
   sucursal quedan cortados por el ejercicio de la raíz. No da error: da un
   número distinto del correcto.
#. **Declaraciones (``account.return``).** Se generan por compañía raíz (o por
   la compañía principal de la unidad fiscal). Una sucursal con ejercicio
   propio no tiene período anual propio: sus declaraciones anuales las arma la
   raíz con el ejercicio de la raíz.

Además, el módulo **no habilita ejercicios explícitos por sucursal**: el
modelo ``account.fiscal.year`` tiene su propio constraint que los prohíbe en
una compañía hija. Si el cliente necesita ejercicios irregulares (de
transición, de más de doce meses), eso queda afuera.

Por eso el módulo **no es auto-instalable y no es parte del set estándar**:
la instalación es la decisión de aceptar esas tres limitaciones para una base
concreta. El análisis completo, con la evidencia en código y las dos
alternativas de implementación evaluadas, está en la tarea **#71643**.

Installation
============

To install this module, you need to:

#. Only install the module

Configuration
=============

To configure this module, you need to:

#. Nada que configurar. Después de instalarlo, el cierre de ejercicio de cada
   sucursal se edita en su propia ficha de compañía.

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

**Al instalarlo sobre una base existente hay que corregir los datos.** El
``create`` de Odoo ya copió el ejercicio de la raíz a cada sucursal cuando se
crearon: levantar la restricción no restaura nada. Hay que escribir el
ejercicio correcto en cada sucursal que corresponda.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/multi-company/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

* |company| |icon|
