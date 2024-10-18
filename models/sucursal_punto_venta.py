from odoo import models, fields, api
import requests


class SucursalPuntoVentaWizard(models.TransientModel):
    # State: Desarrollo Pruebas Alpha
    # Recordatorio: Agregar Wizar o modal personalizado para cambiar la sucursal y punto de venta activos y la Sinconización de la base de datos.

    # Clase: SucursalPuntoVentaWizard
    # - Atributos:
    #   - sucursal_actual: Campo de texto que almacena la sucursal actual seleccionada.
    #   - punto_venta_actual: Campo de texto que almacena el punto de venta actual seleccionado.
    #   - sucursales_html: Campo HTML que almacena la información de las sucursales y puntos de venta.
    #   - sucursal_id: Campo de selección para almacenar la nueva sucursal.
    #   - punto_venta_id: Campo de selección para almacenar el nuevo punto de venta.
    #
    # - Métodos:
    #   - default_get(fields_list): Obtiene los valores por defecto de los campos.
    #   - _compute_actual_sucursal_punto_venta(): Calcula la sucursal y punto de venta actual seleccionados.
    #   - _get_sucursales_html(): Obtiene la información de las sucursales y puntos de venta en formato HTML.
    #   - _onchange_sucursal_id(): Actualiza el campo de selección de punto de venta basado en la sucursal seleccionada.
    #   - action_change_sucursal_punto_venta(): Cambia la sucursal y punto de venta activos.
    #   - get_token_and_url(): Obtiene el token y la URL de la API de la base de datos.
    #   - get_sucursales_puntos_venta(): Obtiene las sucursales y puntos de venta de la API.
    #   - cambiar_sucursal_punto_venta_activo(codigo_sucursal, codigo_punto_venta): Cambia la sucursal y punto de venta activos.
    #   - actualizar_bd_con_nuevos_datos(sucursal_codigo, punto_venta_codigo): Actualiza la base de datos con los nuevos datos.

    _name = 'sucursal.punto.venta.wizard'
    _description = 'Wizard para cambiar Sucursal y Punto de Venta'

    sucursal_actual = fields.Char(
        string="Sucursal Actual", compute="_compute_actual_sucursal_punto_venta")
    punto_venta_actual = fields.Char(
        string="Punto de Venta Actual", compute="_compute_actual_sucursal_punto_venta")
    sucursales_html = fields.Html(
        string="Sucursales y Puntos de Venta", readonly=True)

    sucursal_id = fields.Many2one('sucursal.info', string="Nueva Sucursal")
    punto_venta_id = fields.Many2one(
        'punto.venta.info', string="Nuevo Punto de Venta")

    @api.model
    def default_get(self, fields_list):
        res = super(SucursalPuntoVentaWizard, self).default_get(fields_list)
        if 'sucursales_html' in fields_list:
            res['sucursales_html'] = self._get_sucursales_html()

        sucursales = self.get_sucursales_puntos_venta()
        self.env['sucursal.info'].search([]).unlink()
        self.env['punto.venta.info'].search([]).unlink()

        for sucursal in sucursales:
            sucursal_record = self.env['sucursal.info'].create({
                'codigo': sucursal['codigo'],
                'nombre': f"{sucursal['codigo']} - {sucursal['direccion']}"
            })
            for punto_venta in sucursal['puntosVenta']:
                self.env['punto.venta.info'].create({
                    'codigo': punto_venta['codigo'],
                    'nombre': f"{punto_venta['codigo']} - {punto_venta['nombre']}",
                    'sucursal_id': sucursal_record.id
                })
        return res

    @api.depends()
    def _compute_actual_sucursal_punto_venta(self):
        for record in self:
            config = self.env['isi_pass_config'].search(
                [('user_id', '=', self.env.user.id)], limit=1)
            record.sucursal_actual = f"{
                config.sucursal_codigo} - {config.sucursal_direccion}"
            record.punto_venta_actual = f"{
                config.punto_venta_codigo} - {config.punto_venta_nombre}"

    def _get_sucursales_html(self):
        sucursales = self.get_sucursales_puntos_venta()
        html = "<div class='container'>"
        for sucursal in sucursales:
            html += f"""
                <div class="card mb-3">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">SUCURSAL {sucursal['codigo']}</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Departamento:</strong> {sucursal['departamento']['departamento']}</p>
                        <p><strong>Municipio:</strong> {sucursal['municipio']}</p>
                        <p><strong>Dirección:</strong> {sucursal['direccion']}</p>
                        <p><strong>Teléfono:</strong> {sucursal['telefono']}</p>
                        <h6 class="mt-4">Puntos de Venta:</h6>
                        <div class="list-group">
            """
            for punto_venta in sucursal['puntosVenta']:
                html += f"""
                    <div class="list-group-item">
                        <h6 class="mb-1">PUNTO DE VENTA {punto_venta['codigo']}</h6>
                        <p class="mb-1"><strong>Nombre:</strong> {punto_venta['nombre']}</p>
                        <p class="mb-1"><strong>Descripción:</strong> {punto_venta['descripcion']}</p>
                    </div>
                """
            html += """
                        </div>
                    </div>
                </div>
            """
        html += "</div>"
        return html

    @api.onchange('sucursal_id')
    def _onchange_sucursal_id(self):
        self.punto_venta_id = False
        return {'domain': {'punto_venta_id': [('sucursal_id', '=', self.sucursal_id.id)]}}

    def action_change_sucursal_punto_venta(self):
        self.ensure_one()
        if self.sucursal_id and self.punto_venta_id:
            result = self.cambiar_sucursal_punto_venta_activo(
                self.sucursal_id.codigo, self.punto_venta_id.codigo)
            if result:
                self.actualizar_bd_con_nuevos_datos(
                    self.sucursal_id.codigo, self.punto_venta_id.codigo)
                return {'type': 'ir.actions.client', 'tag': 'reload'}
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Error',
                'message': 'No se pudo cambiar la sucursal y punto de venta.',
                'type': 'warning',
            }
        }

    @api.model
    def get_token_and_url(self):
        current_user_id = self.env.user.id
        self.env.cr.execute("""
            SELECT token, api_url FROM isi_pass_config
            WHERE user_id = %s
            LIMIT 1
        """, (current_user_id,))
        result = self.env.cr.fetchone()
        return result if result else (None, None)

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
            response = requests.post(api_url, headers=headers, json={
                                     'query': mutation, 'variables': variables})
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


class SucursalInfo(models.TransientModel):

    # Clase: SucursalInfo
    # - Atributos:
    #   - codigo: Campo entero que almacena el código de la sucursal.
    #   - nombre: Campo de texto que almacena el nombre de la sucursal.
    #
    # - Métodos:
    #   - No tiene métodos.

    _name = 'sucursal.info'
    _description = 'Información de Sucursal'

    codigo = fields.Integer(string="Código")
    nombre = fields.Char(string="Nombre")


class PuntoVentaInfo(models.TransientModel):

    # Clase: PuntoVentaInfo
    # - Atributos:
    #   - codigo: Campo entero que almacena el código del punto de venta.
    #   - nombre: Campo de texto que almacena el nombre del punto de venta.
    #   - sucursal_id: Campo de selección que almacena la sucursal a la que pertenece el punto de venta.
    #
    # - Métodos:
    #   - No tiene métodos.

    _name = 'punto.venta.info'
    _description = 'Información de Punto de Venta'

    codigo = fields.Integer(string="Código")
    nombre = fields.Char(string="Nombre")
    sucursal_id = fields.Many2one('sucursal.info', string="Sucursal")
