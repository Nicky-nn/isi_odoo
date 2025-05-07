from odoo import api, fields, models

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

    # Nuevos campos para almacenar y mostrar los códigos SIAT
    sucursal_codigo_siat = fields.Char(
        string='SIAT Sucursal Código',
        compute='_compute_siat_codes',
        readonly=True,
        # store=True # Considera store=True si los valores no cambian frecuentemente por usuario
    )
    punto_venta_codigo_siat = fields.Char(
        string='SIAT Punto de Venta Código',
        compute='_compute_siat_codes',
        readonly=True,
        # store=True
    )

    # Método helper para obtener valores de 'isi_pass_config'
    # Adaptado de tu _get_api_config en PosOrder
    def _get_value_from_isi_pass_config(self, column_name, user_id):
        self.ensure_one() # Asegura que operamos sobre un solo registro de config
        allowed_columns = {'sucursal_codigo', 'punto_venta_codigo'}

        if column_name not in allowed_columns:
            return None # En un campo computado, es mejor devolver None que lanzar un error que rompa la UI

        # Asegúrate que los nombres de tabla y columna son seguros.
        # Aquí, column_name es validado contra allowed_columns.
        query = f"SELECT \"{column_name}\" FROM isi_pass_config WHERE user_id = %s LIMIT 1"
        self.env.cr.execute(query, (user_id,))
        row = self.env.cr.fetchone()

        if not row:
            return None
        
        try:
            # Los códigos pueden ser numéricos pero también alfanuméricos o con ceros a la izquierda.
            # Devolver como string es más seguro para visualización.
            return str(row[0]) if row[0] is not None else None
        except (ValueError, TypeError) as e:
            return None
    
    @api.depends('allow_siat_customer') # Se recalcula si 'allow_siat_customer' cambia.
    def _compute_siat_codes(self):
        # El usuario actual que está abriendo la sesión del POS
        current_user_id = self.env.user.id
        for config in self:
            if config.allow_siat_customer:
                sucursal_code = config._get_value_from_isi_pass_config('sucursal_codigo', current_user_id)
                pdv_code = config._get_value_from_isi_pass_config('punto_venta_codigo', current_user_id)
                
                config.sucursal_codigo_siat = sucursal_code
                config.punto_venta_codigo_siat = pdv_code
            else:
                config.sucursal_codigo_siat = False # Odoo trata Char False como un string vacío en la UI
                config.punto_venta_codigo_siat = False

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