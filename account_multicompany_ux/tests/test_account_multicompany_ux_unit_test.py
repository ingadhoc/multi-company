import odoo.tests.common as common
from odoo import Command, fields
from datetime import timedelta


class TestAccountMulticompanyUxUnitTest(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.first_company = self.env['res.company'].search([], limit=1)
        self.second_company = self.env['res.company'].search([('id', '!=', self.first_company.id)], limit=1)
        if not self.second_company:
            self.second_company = self.env['res.company'].create({'name': 'Test Company 2'})
            
        self.partner_ri = self.env['res.partner'].search([], limit=1)

        self.first_company_journal = self.env['account.journal'].search([('company_id', '=', self.first_company.id), ('type', '=', 'sale')], limit=1)
        self.second_company_journal = self.env['account.journal'].search([('company_id', '=', self.second_company.id), ('type', '=', 'sale')], limit=1)
        if not self.second_company_journal:
            
            a_sale = self.env['account.account'].create({
                'code': 'X2020',
                'name': 'Product Sales - (test)',
                'account_type': 'income',
                'company_id': self.second_company.id,
            })

            a_receivable = self.env['account.account'].create({
                'code': 'X2021',
                'name': 'Product Sales Receivable - (test)',
                'account_type': 'asset_receivable',
                'company_id': self.second_company.id,
            })

            self.second_company_journal = self.env['account.journal'].create({
                'name': 'Second Customer Invoices - Test',
                'code': 'TINV',
                'type': 'sale',
                'default_account_id': a_sale.id,
                'company_id': self.second_company.id,
            })
        
        self.bank_1 = self.env['res.partner.bank'].search([('company_id','=', False)], limit=1)
        self.bank_1.write({'partner_id': self.first_company.partner_id.id})
        self.bank_1.company_id = self.first_company.id
        self.bank_1.allow_out_payment = True
        self.env.company = self.first_company

    def test_multicompany_sale_order(self):
        """Cambio de compañía de una factura que cuenta con res partner bank seteado para la compañia original"""
        invoice = self.env['account.move'].create({
            'partner_id': self.partner_ri.id,
            'invoice_date': self.today,
            'move_type': 'out_invoice',
            'journal_id': self.first_company_journal.id,
            'company_id': self.first_company.id,
            'partner_bank_id': self.bank_1.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.env.ref('product.product_product_16').id,
                    'quantity': 1,
                    'price_unit': 100,
                }),
            ],
        })

        acc = self.env['account.change.company'].create({
            'move_id': invoice.id,
            'company_ids': [self.first_company.id, self.second_company.id],
            'company_id': self.second_company.id,
            'journal_id': self.second_company_journal.id
        })
        acc.change_company()
        self.assertEqual(invoice.partner_bank_id.id,  False , "No se realizo de forma correcta el cambio partner_bank_id al cambiar la compañia")
        acc = self.env['account.change.company'].create({
            'move_id': invoice.id,
            'company_ids': [self.first_company.id, self.second_company.id],
            'company_id': self.first_company.id,
            'journal_id': self.first_company_journal.id
        })
        self.bank_1.company_id = False
        invoice.write({"partner_bank_id": self.bank_1.id})

        acc.change_company()
        self.assertEqual(invoice.partner_bank_id.id,  self.bank_1.id , "No se realizo de forma correcta el cambio partner_bank_id al cambiar la compañia")
        invoice.action_post()
