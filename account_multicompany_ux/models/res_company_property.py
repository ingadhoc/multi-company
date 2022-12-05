##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo import tools
from lxml import etree
from ast import literal_eval
import logging
import json
_logger = logging.getLogger(__name__)


class ResCompanyProperty(models.Model):
    """
    We dont use res.company because most user dont' have access rights to edit
    it
    """
    _name = "res.company.property"
    _description = "Company Property"
    _auto = False
    # _rec_name = 'display_name'
    _depends = {
        'res.company': [
            'id',
        ],
    }

    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
    )

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, self._table)
        query = """
            SELECT
                c.id as id,
                c.id as company_id
            FROM
                res_company c
        """
        cr.execute("""CREATE or REPLACE VIEW %s as (%s
        )""" % (self._table, query))

    property_field = fields.Char(
        compute='_compute_property_field',
    )
    property_account_id = fields.Many2one(
        'account.account',
        string='Account',
        compute='_compute_property_account',
        inverse='_inverse_property_account',
    )
    property_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Term',
        compute='_compute_property_term',
        inverse='_inverse_property_term',
    )
    property_position_id = fields.Many2one(
        'account.fiscal.position',
        string='Fiscal Position',
        compute='_compute_property_position',
        inverse='_inverse_property_position',
    )
    property_pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
        compute='_compute_property_pricelist',
        inverse='_inverse_property_pricelist',
    )
    standard_price = fields.Float(
        string="standard_price",
        compute='_compute_property_standard_price',
        inverse='_inverse_property_standard_price',
        digits='Product Price',
    )
    # display_name = fields.Char(
    #     compute='_compute_display_name'
    # )

    @api.model
    def _get_companies(self):
        domain = []
        comodel = self._get_property_comodel()
        if comodel in ['account.account']:
            domain = [('company_id.consolidation_company', '=', False)]
        return self.search(domain)

    @api.model
    def action_company_properties(self):
        property_field = self._context.get('property_field', False)
        if not property_field:
            return True

        company_properties = self._get_companies()
        action_read = self.env["ir.actions.actions"]._for_xml_id(
            'account_multicompany_ux.action_res_company_property')
        # do this because raise an error if came from a view
        #  with group_by activated
        ctx = self._context.copy()
        ctx.pop('group_by', None)
        action_read['context'] = ctx
        action_read['domain'] = [('id', 'in', company_properties.ids)]
        return action_read

    @api.model
    def _get_property_comodel(self):
        property_field = self._context.get('property_field')
        record = self._get_record()
        if record:
            field = self._get_record()._fields.get(property_field)
            return field and field.comodel_name or False

    @api.model
    def _get_record(self):
        context = self._context
        active_model = context.get('active_model')
        active_id = context.get('active_id')
        property_field = context.get('property_field')
        if not property_field or not active_id or not active_model:
            _logger.warn(
                'Could not get property record from context %s' % context)
            return False
        return self.with_company(self.id).env[active_model].browse(active_id)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        """
        Con esta funcion hacemos dos cosas:
        1. Mostrar solo la columna que corresponda segun el modelo
        2. Agregar dominio segun el dominio original de la porperty mas de cia
        """
        res = super(ResCompanyProperty, self).get_view(view_id, view_type, **options)
        doc = etree.XML(res['arch'])
        property_field = self._context.get('property_field')
        domain = self._context.get('property_domain')
        record = self._get_record()
        if record:
            field = self._get_record()._fields.get(property_field)
            # si no viene definido un property_domain buscamos uno para
            # definido en el campo de la property
            if not domain:
                try:
                    domain = literal_eval(field.domain)
                except:
                    domain = []
            domain_elements = [str(x) for x in domain]

            # add company domain if comodel has company
            comodel = self._get_property_comodel()
            if comodel:
                if self.env[comodel]._fields.get('company_id'):
                    domain_elements += [
                        "'|'",
                        "('company_id', '=', False)",
                        "('company_id', '=', company_id)"]
            str_domain = '[%s]' % ','.join(domain_elements)

            company_property_field = self._get_company_property_field()
            xpath = "//field[@name='%s']" % company_property_field
            for node in doc.xpath(xpath):
                node.set('domain', str(str_domain))
                node.set('invisible', '0')
                modifiers = json.loads(node.get("modifiers"))
                modifiers['column_invisible'] = False
                node.set("modifiers", json.dumps(modifiers))

        res['arch'] = etree.tostring(doc)
        return res

    @api.model
    def _get_company_property_field(self):
        comodel = self._get_property_comodel()
        if comodel == 'account.account':
            company_property_field = 'property_account_id'
        elif comodel == 'account.fiscal.position':
            company_property_field = 'property_position_id'
        elif comodel == 'account.payment.term':
            company_property_field = 'property_term_id'
        elif comodel == 'product.pricelist':
            company_property_field = 'property_pricelist_id'
        else:
            property_field = self._context.get('property_field')
            if property_field == 'standard_price':
                company_property_field = 'standard_price'
            else:
                raise UserError(
                    _('Property for model %s not implemented yet' % comodel))
        return company_property_field

    def name_get(self):
        """
        No llamamos a super porque tendriamos que igualmente hacer un read
        para obtener la compania y no queremos disminuir la performance
        """
        # por ahora en campos calculados no podemos cambiar el contexto de esta
        # manera
        # for rec in self.with_context(no_company_sufix=True):
        res = []
        for rec in self:
            company_field = getattr(
                rec.with_context(no_company_sufix=True),
                rec._get_company_property_field())
            if type(company_field) is float:
                precision_digits = self.env['decimal.precision'].precision_get(
                    'Product Price')
                # por alguna razon el float_round no nos está funcionando
                # y usamos round directamente (por ej. para valor 42,66)
                company_field = company_field and round(
                    company_field, precision_digits)
                # company_field = company_field and float_round(
                #     company_field, precision_digits=precision_digits)
                display_name = '%s%s' % (
                    company_field or _('None'),
                    rec.company_id.get_company_sufix())
            else:
                display_name = '%s%s' % (
                    company_field.display_name or _('None'),
                    rec.company_id.get_company_sufix())
            res.append((rec.id, display_name))
        return res

    def _compute_property_field(self):
        for record in self:
            record.property_field = self._context.get('property_field', '')

    def _get_property_value(self):
        self.ensure_one()
        property_field = self.property_field
        record = self._get_record()
        if not record or not property_field:
            return False
        return getattr(
            record,
            property_field)

    def _compute_property_standard_price(self):
        for record in self:
            if record.property_field == 'standard_price':
                record.standard_price = record._get_property_value()
            else:
                record.standard_price = False

    def _compute_property_account(self):
        for record in self:
            if record._get_property_comodel() == 'account.account':
                record.property_account_id = record._get_property_value()
            else:
                record.property_account_id = False

    def _compute_property_position(self):
        for record in self:
            if record._get_property_comodel() == 'account.fiscal.position':
                record.property_position_id = record._get_property_value()
            else:
                record.property_position_id = False

    def _compute_property_term(self):
        for record in self:
            if record._get_property_comodel() == 'account.payment.term':
                record.property_term_id = record._get_property_value()
            else:
                record.property_term_id = False

    def _compute_property_pricelist(self):
        for record in self:
            if record._get_property_comodel() == 'product.pricelist':
                record.property_pricelist_id = record._get_property_value()
            else:
                record.property_pricelist_id = False

    def _set_property_value(self, value):
        self.ensure_one()
        record = self._get_record()
        property_field = self.property_field
        if not record or not property_field:
            return True
        setattr(
            record,
            property_field,
            value)

    def _inverse_property_account(self):
        for rec in self:
            rec._set_property_value(rec.property_account_id.id)

    def _inverse_property_position(self):
        for rec in self:
            rec._set_property_value(rec.property_position_id.id)

    def _inverse_property_term(self):
        for rec in self:
            rec._set_property_value(rec.property_term_id.id)

    def _inverse_property_pricelist(self):
        for rec in self:
            rec._set_property_value(rec.property_pricelist_id.id)

    def _inverse_property_standard_price(self):
        for rec in self:
            rec._set_property_value(rec.standard_price)
