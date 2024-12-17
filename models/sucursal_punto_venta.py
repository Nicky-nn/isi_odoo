from odoo import models, fields, api
import requests


class SucursalPuntoVentaWizard(models.TransientModel):
    _name = 'sucursal.punto.venta.wizard'
    _description = 'Asistente para cambiar Sucursal y Punto de Venta'

    sucursal_actual = fields.Char(string="Sucursal Actual", readonly=True)
    punto_venta_actual = fields.Char(
        string="Punto de Venta Actual", readonly=True)
    nueva_sucursal = fields.Selection(
        selection='_get_sucursales', string="Código Sucursal")
    nuevo_punto_venta = fields.Selection(
        selection='_get_puntos_venta', string="Código Punto de Venta")

    def _obtener_token_y_url(self):
        self.env.cr.execute("""
            SELECT token, api_url FROM isi_pass_config
            WHERE user_id = %s LIMIT 1
        """, (self.env.user.id,))
        result = self.env.cr.fetchone()
        return result if result else (None, None)

    @api.model
    def _get_sucursales(self):
        sucursales = self.get_sucursales_puntos_venta()
        return [(str(suc['codigo']), f"{suc['direccion']} (Código: {suc['codigo']})") for suc in sucursales]

    @api.model
    def _get_puntos_venta(self):
        sucursales = self.get_sucursales_puntos_venta()
        puntos = []
        for suc in sucursales:
            for punto in suc.get('puntosVenta', []):
                puntos.append((str(punto['codigo']), f"{
                              punto['nombre']} (Código: {punto['codigo']})"))
        return puntos

    @api.model
    def default_get(self, fields_list):
        res = super(SucursalPuntoVentaWizard, self).default_get(fields_list)

        # Obtener los valores actuales desde isi_pass_config
        self.env.cr.execute("""
            SELECT sucursal_codigo, sucursal_direccion, punto_venta_codigo, punto_venta_nombre 
            FROM isi_pass_config 
            WHERE user_id = %s LIMIT 1
        """, (self.env.user.id,))
        current_values = self.env.cr.fetchone()

        if current_values:
            sucursal_codigo, sucursal_direccion, punto_venta_codigo, punto_venta_nombre = current_values
            res.update({
                'sucursal_actual': f"{sucursal_direccion} (Código: {sucursal_codigo})" if sucursal_direccion and sucursal_codigo else '',
                'punto_venta_actual': f"{punto_venta_nombre} (Código: {punto_venta_codigo})" if punto_venta_nombre and punto_venta_codigo else '',
                'nueva_sucursal': str(sucursal_codigo) if sucursal_codigo else '',
                'nuevo_punto_venta': str(punto_venta_codigo) if punto_venta_codigo else '',
            })
        else:
            res.update({
                'sucursal_actual': '',
                'punto_venta_actual': '',
                'nueva_sucursal': '',
                'nuevo_punto_venta': '',
            })

        return res

    def get_sucursales_puntos_venta(self):
        token, api_url = self._obtener_token_y_url()
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
                    direccion
                    telefono
                    puntosVenta {
                        codigo
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
        token, api_url = self._obtener_token_y_url()
        if not token or not api_url:
            return False

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
                return response.json().get('data', {}).get('usuarioCambiarSucursalPuntoVentaActivo') is not None
            else:
                return False
        except requests.exceptions.RequestException:
            return False

    def action_cambiar_sucursal_punto_venta(self):
        exito = self.cambiar_sucursal_punto_venta_activo(
            self.nueva_sucursal, self.nuevo_punto_venta)
        if exito:
            # Obtener detalles de la nueva sucursal y punto de venta
            sucursales = self.get_sucursales_puntos_venta()
            nueva_sucursal_info = next(
                (suc for suc in sucursales if str(suc['codigo']) == self.nueva_sucursal), None)
            nuevo_punto_venta_info = None
            if nueva_sucursal_info:
                nuevo_punto_venta_info = next(
                    (punto for punto in nueva_sucursal_info.get('puntosVenta', []) if str(punto['codigo']) == self.nuevo_punto_venta), None)

            # Actualizar la tabla isi_pass_config directamente mediante SQL
            if nueva_sucursal_info and nuevo_punto_venta_info:
                self.env.cr.execute("""
                    UPDATE isi_pass_config
                    SET
                        sucursal_codigo = %s,
                        sucursal_direccion = %s,
                        sucursal_telefono = %s,
                        punto_venta_codigo = %s,
                        punto_venta_nombre = %s,
                        punto_venta_descripcion = %s,
                        write_uid = %s,
                        write_date = NOW()
                    WHERE user_id = %s
                """, (
                    self.nueva_sucursal,
                    nueva_sucursal_info.get('direccion'),
                    nueva_sucursal_info.get('telefono'),
                    self.nuevo_punto_venta,
                    nuevo_punto_venta_info.get('nombre'),
                    nuevo_punto_venta_info.get('descripcion'),
                    self.env.uid,
                    self.env.user.id
                ))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Éxito',
                    'message': 'Sucursal y Punto de Venta cambiados exitosamente.',
                    'type': 'success',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',  # Acción para recargar la página
                    }
                }
            }

        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'No se pudo cambiar la Sucursal y Punto de Venta.',
                    'type': 'danger',
                    'sticky': False,
                }
            }
