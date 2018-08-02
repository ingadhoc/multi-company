##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo import tools
from lxml import etree
from ast import literal_eval
from odoo.osv.orm import setup_modifiers
import logging
_logger = logging.getLogger(__name__)


class ResCompanyProperty(models.Model):
    """
    We dont use res.company because most user dont' have access rights to edit
    it
    """
    _name = "res.company.property"
    _description = "Company Property"
    _auto = False
    _rec_name = 'display_name'
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

    @api.model_cr
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
    display_name = fields.Char(
        compute='_compute_display_name'
    )

    @api.model
    def _get_companies(self):
        domain = []
        comodel = self._get_property_comodel()
        if comodel not in [
                'account.payment.term', 'product.pricelist',
                'account.fiscal.position']:
            domain = [('company_id.consolidation_company', '=', False)]
        return self.search(domain)

    @api.model
    def action_company_properties(self):
        property_field = self._context.get('property_field', False)
        if not property_field:
            return True

        company_properties = self._get_companies()
        action = self.env.ref(
            'account_multicompany_ux.action_res_company_property')

        if not action:
            return False
        action_read = action.read()[0]
        action_read['context'] = self._context
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
        return self.with_context(
            force_company=self.id).env[active_model].browse(
            active_id)

    @api.model
    def fields_view_get(
            self, view_id=None, view_type='form', toolbar=False,
            submenu=False):
        """
        Con esta funcion hacemos dos cosas:
        1. Mostrar solo la columna que corresponda segun el modelo
        2. Agregar dominio segun el dominio original de la porperty mas de cia
        """
        res = super(ResCompanyProperty, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)
        doc = etree.XML(res['arch'])
        property_field = self._context.get('property_field')
        domain = self._context.get('property_domain')
        record = self._get_record()
        if record:
            field = self._get_record()._fields.get(property_field)
            # si no viene definido un property_domain buscamos uno para
            # definido ene l campo de la property
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
                # modifiers make still invisible = 1
                setup_modifiers(node, res['fields'][company_property_field])
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
            raise Warning(
                _('Property for model %s not implemented yet' % comodel))
        return company_property_field

    @api.multi
    def _compute_display_name(self):
        """
        No llamamos a super porque tendriamos que igualmente hacer un read
        para obtener la compania y no queremos disminuir la performance
        """
        # por ahora en campos calculados no podemos cambiar el contexto de esta
        # manera
        # for rec in self.with_context(no_company_sufix=True):
        for rec in self:
            company_field = getattr(
                rec.with_context(no_company_sufix=True),
                rec._get_company_property_field())
            display_name = '%s%s' % (
                company_field.display_name or _('None'),
                rec.company_id.get_company_sufix())
            rec.display_name = display_name

    @api.depends()
    def _compute_property_field(self):
        for record in self:
            record.property_field = self._context.get('property_field', '')

    @api.multi
    def _get_property_value(self):
        self.ensure_one()
        property_field = self.property_field
        record = self._get_record()
        if not record or not property_field:
            return False
        return getattr(
            record,
            property_field)

    @api.depends()
    def _compute_property_account(self):
        for record in self:
            if record._get_property_comodel() == 'account.account':
                record.property_account_id = record._get_property_value()

    @api.depends()
    def _compute_property_position(self):
        for record in self:
            if record._get_property_comodel() == 'account.fiscal.position':
                record.property_position_id = record._get_property_value()

    @api.depends()
    def _compute_property_term(self):
        for record in self:
            if record._get_property_comodel() == 'account.payment.term':
                record.property_term_id = record._get_property_value()

    @api.depends()
    def _compute_property_pricelist(self):
        for record in self:
            if record._get_property_comodel() == 'product.pricelist':
                record.property_pricelist_id = record._get_property_value()

    @api.multi
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

    @api.multi
    def _inverse_property_account(self):
        for rec in self:
            rec._set_property_value(rec.property_account_id.id)

    @api.multi
    def _inverse_property_position(self):
        for rec in self:
            rec._set_property_value(rec.property_position_id.id)

    @api.multi
    def _inverse_property_term(self):
        for rec in self:
            rec._set_property_value(rec.property_term_id.id)

    @api.multi
    def _inverse_property_pricelist(self):
        for rec in self:
            rec._set_property_value(rec.property_pricelist_id.id)
