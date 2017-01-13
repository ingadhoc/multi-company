# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'category': 'Accounting & Finance',
    'data': [
        # 'security/rule.xml',
        'views/account_invoice_view.xml',
        'views/account_move_view.xml',
        'data/account_reconcile_data.xml',
        # 'views/account_move_view.xml',
        # 'wizard/account_move_line_reconcile_writeoff_view.xml',
        # 'wizard/account_statement_from_invoice_view.xml',
    ],
    'demo': [],
    'depends': ['account'],
    'description': '''
Account Multi Company Fixes
===========================
TODO:
arreglar para los statments, por ahora no pudismo hacer que nade bien, sobre todo la parte de que 
cuentas ofrece para seleccionar. Tal vez podemos ver de dejar eso de esa manera.
Al respecto de como se genera esto esta este codigo:
<table class="o_group o_inner_group o_group_col_6 create_group_right"><!-- here come some form_create_field --></table>

A su vez hay que cambiar self.env.user.company_id por self.journal_id.company_id en "account.bank.statement", tal vez un pr a odoo?
''',
    'installable': True,
    'name': 'Account Multi Company Fixes',
    'test': [],
    'version': '9.0.1.2.0',
}
