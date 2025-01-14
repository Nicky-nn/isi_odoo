from odoo import models, fields, api
import requests


class SucursalPuntoVentaAPI(models.TransientModel):

    # State: Desarrollo
    # Esta clase se encarga de manejar la consulta a la API para obtener las sucursales y puntos de venta.
    #
    # Atributos:
    # - sucursales_html: Campo HTML que almacena la información de las sucursales y puntos de venta.
    # - sucursal_actual: Campo de texto que almacena la sucursal actual seleccionada.
    # - punto_venta_actual: Campo de texto que almacena el punto de venta actual seleccionado.
    #
    # Métodos:
    # - default_get(fields_list): Obtiene los valores por defecto de los campos.
    # - _get_sucursales_html(): Obtiene la información de las sucursales y puntos de venta en formato HTML.
    # - get_token_and_url(): Obtiene el token y la URL de la API de la base de datos.
    # - get_sucursales_puntos_venta(): Obtiene las sucursales y puntos de venta de la API.
    # - action_change_sucursal_punto_venta(sucursal_codigo, punto_venta_codigo): Cambia la sucursal y punto de venta activos.

    _name = 'sucursal.punto.venta.api'
    _description = 'Consulta API para Sucursales y Puntos de Venta'

    sucursales_html = fields.Html(
        string="Sucursales y Puntos de Venta", readonly=True)
    sucursal_actual = fields.Char(
        string="Sucursal Actual", compute="_compute_actual_sucursal_punto_venta")
    punto_venta_actual = fields.Char(
        string="Punto de Venta Actual", compute="_compute_actual_sucursal_punto_venta")

    @api.model
    def default_get(self, fields_list):
        res = super(SucursalPuntoVentaAPI, self).default_get(fields_list)
        if 'sucursales_html' in fields_list:
            res['sucursales_html'] = self._get_sucursales_html()
        return res

    def _get_sucursales_html(self):
        sucursales = self.get_sucursales_puntos_venta()
        html = "<div class='container'>"
        for sucursal in sucursales:
            html += f"""
                <div class="row mb-3">
                    <div class="col-12">
                        <div class="alert alert-info">
                            <strong>SUCURSAL {sucursal['codigo']}</strong> / {sucursal['departamento']['departamento']} -
                            {sucursal['municipio']} / \
                                {sucursal['direccion']} / \
                                    {sucursal['telefono']}
                        </div>
                    </div>
                </div>
            """
            for punto_venta in sucursal['puntosVenta']:
                html += f"""
            <div class="alert alert-warning">
                <strong>PUNTO DE VENTA {punto_venta['codigo']}</strong><br>
                <span><strong>Nombre:</strong> {punto_venta['nombre']}</span><br>
                <span><strong>Descripción:</strong> {punto_venta['descripcion']}</span><br><br>
                <a href="#" class="btn btn-primary" onclick="document.getElementById('sucursal_codigo').value='{sucursal['codigo']}';">
                    Seleccionar Sucursal
                </a>
            </div>
            <hr>
        """
        html += "</div>"
        return html

    @api.depends()
    def _compute_actual_sucursal_punto_venta(self):
        for record in self:
            config = self.env['isi_pass_config'].search([('user_id', '=', self.env.user.id)], limit=1)
            record.sucursal_actual = f"{config.sucursal_codigo} - {config.sucursal_direccion}"
            record.punto_venta_actual = f"{config.punto_venta_codigo} - {config.punto_venta_nombre}"
    @api.model
    def get_token_and_url(self):
        current_user_id = self.env.user.id
        self.env.cr.execute("""
            SELECT token, api_url FROM isi_pass_config
            WHERE user_id = %s
            LIMIT 1
        """, (current_user_id,))
        result = self.env.cr.fetchone()
        if result:
            return result
        return None, None

    @api.model
    def get_sucursales_puntos_venta(self):
        token, api_url = self.get_token_and_url()
        if not token or not api_url:
            return []

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        query = """
        query MI_RESTRICCION {
            usuarioRestriccion {
                sucursales {
                    codigo
                    telefono
                    direccion
                    municipio
                    departamento {
                        departamento
                    }
                    puntosVenta {
                        codigo
                        tipoPuntoVenta {
                            codigoClasificador
                            descripcion
                        }
                        nombre
                        descripcion
                    }
                }
            }
        }
        """

        try:
            response = requests.post(
                api_url, headers=headers, json={'query': query})
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('usuarioRestriccion', {}).get('sucursales', [])
            else:
                return []
        except requests.exceptions.RequestException:
            return []

    @api.model
    def action_change_sucursal_punto_venta(self, sucursal_codigo, punto_venta_codigo):
        print(" Punta de venta codigo: ", punto_venta_codigo,
              " Sucursal codigo: ", sucursal_codigo)
        if sucursal_codigo and punto_venta_codigo:
            result = self.cambiar_sucursal_punto_venta_activo(
                sucursal_codigo, punto_venta_codigo)
            if result:
                self.actualizar_bd_con_nuevos_datos(
                    sucursal_codigo, punto_venta_codigo)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Error',
                'message': 'No se pudo cambiar la sucursal y punto de venta.',
                'type': 'warning',
            }
        }

    def cambiar_sucursal_punto_venta_activo(self, codigo_sucursal, codigo_punto_venta):
        token, api_url = self.get_token_and_url()
        if not token or not api_url:
            return None

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        mutation = """
        mutation CAMBIAR_SUCURSAL_PUNTO_VENTA_ACTIVO($codigoSucursal: Int!, $codigoPuntoVenta: Int!) {
            usuarioCambiarSucursalPuntoVentaActivo(
                codigoSucursal: $codigoSucursal
                codigoPuntoVenta: $codigoPuntoVenta
            ) {
                nombres
                restriccionActivo {
                    codigoSucursal
                    codigoPuntoVenta
                }
            }
        }
        """

        variables = {
            "codigoSucursal": int(codigo_sucursal),
            "codigoPuntoVenta": int(codigo_punto_venta)
        }

        try:
            response = requests.post(
                api_url, headers=headers, json={'query': mutation, 'variables': variables})
            if response.status_code == 200:
                return response.json().get('data', {}).get('usuarioCambiarSucursalPuntoVentaActivo')
            else:
                return None
        except requests.exceptions.RequestException:
            return None

    def actualizar_bd_con_nuevos_datos(self, sucursal_codigo, punto_venta_codigo):
        sucursales = self.get_sucursales_puntos_venta()
        sucursal = next(
            (s for s in sucursales if s['codigo'] == sucursal_codigo), None)
        if sucursal:
            punto_venta = next(
                (pv for pv in sucursal['puntosVenta'] if pv['codigo'] == punto_venta_codigo), None)
            if punto_venta:
                self.env.cr.execute("""
                    UPDATE isi_pass_config
                    SET sucursal_codigo = %s,
                        sucursal_direccion = %s,
                        sucursal_telefono = %s,
                        departamento_codigo = %s,
                        departamento_nombre = %s,
                        punto_venta_codigo = %s,
                        punto_venta_nombre = %s,
                        punto_venta_descripcion = %s
                    WHERE user_id = %s
                """, (
                    sucursal['codigo'],
                    sucursal['direccion'],
                    sucursal['telefono'],
                    sucursal['departamento'].get('codigo', ''),
                    sucursal['departamento'].get('departamento', ''),
                    punto_venta['codigo'],
                    punto_venta['nombre'],
                    punto_venta['descripcion'],
                    self.env.user.id
                ))
                self.env.cr.commit()
