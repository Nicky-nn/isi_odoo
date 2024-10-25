from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_allow_siat_customer = fields.Boolean(
        related='pos_config_id.allow_siat_customer',
        readonly=False,
        string='Permitir Configuración según SIAT'
    )

class PosConfig(models.Model):
    _inherit = 'pos.config'

    allow_siat_customer = fields.Boolean(
        string='Permitir Configuracíon según SIAT',
        help='Si está activado, solo se mostrarán campos específicos del SIAT en el PDV'
    )

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        result = super()._loader_params_res_partner()
        result['search_params']['fields'].extend([
            'codigo_tipo_documento_identidad',
            'complemento',
            'razon_social'
        ])
        return result