import requests
from odoo import models, fields, api


class ProductTemplate(models.Model):
    # State: Compleado
    # Recordatorio: Cambiar el nombre a isi_productos_homologados.py
    # Clase que representa un producto en el sistema.
    # - Atributos:
    #   - codigo_producto_homologado: Campo de selección para almacenar el código del producto homologado.
    #   - codigo_unidad_medida: Campo de selección para almacenar el código de la unidad de medida.
    #
    # - Métodos:
    #   - _get_codigo_producto_options: Método que obtiene los códigos de productos homologados desde una API externa y devuelve una lista de selección.
    #   - _get_codigo_unidad_medida_options: Método que obtiene los códigos de unidades de medida desde una API externa y devuelve una lista de selección.
    #   - _get_api_data(query): Método que realiza una consulta a la API para obtener los datos necesarios.

    _inherit = 'product.template'

    codigo_producto_homologado = fields.Selection(
        selection='_get_codigo_producto_options',
        string='Código Producto Homologado'
    )
    codigo_unidad_medida = fields.Selection(
        selection='_get_codigo_unidad_medida_options',
        string='Código Unidad de Medida'
    )

    def _get_api_data(self, query):
        api_model = self.env['isi.pass.config.api']
        api_data = api_model.get_api_data_for_user()
        if not api_data:
            return {'data': {'sinProductoServicio': [], 'sinUnidadMedida': []}}

        token, api_url = api_data

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            response = requests.post(
                api_url, json={'query': query}, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {'data': {'sinProductoServicio': [], 'sinUnidadMedida': []}}
        except requests.exceptions.RequestException:
            return {'data': {'sinProductoServicio': [], 'sinUnidadMedida': []}}

    @api.model
    def _get_codigo_producto_options(self):
        query = """
        query {
            sinProductoServicio {
                codigoActividad
                codigoProducto
                descripcionProducto
            }
        }
        """
        data = self._get_api_data(query)
        sin_producto_servicio = data.get(
            'data', {}).get('sinProductoServicio', [])

        return [
            (f"{item['codigoActividad']} - {item['codigoProducto']} - {item['descripcionProducto']}",
             f"{item['codigoActividad']} - {item['codigoProducto']} - {item['descripcionProducto']}")
            for item in sin_producto_servicio
        ]

    @api.model
    def _get_codigo_unidad_medida_options(self):
        query = """
        query {
            sinUnidadMedida {
                codigoClasificador
                descripcion
            }
        }
        """
        data = self._get_api_data(query)
        sin_unidad_medida = data.get('data', {}).get('sinUnidadMedida', [])

        return [
            (f"{item['codigoClasificador']} - {item['descripcion']}",
             f"{item['codigoClasificador']} - {item['descripcion']}")
            for item in sin_unidad_medida
        ]


class IsiPassConfigAPI(models.TransientModel):
    # State: Completado
    # Se utiliza para consultar la API de ISI Pass Config.
    # - Métodos:
    #   - get_api_data_for_user: Método que obtiene los datos de la API para el usuario actual.

    _name = 'isi.pass.config.api'
    _description = 'Consulta API de ISI Pass Config'

    @api.model
    def get_api_data_for_user(self):
        current_user_id = self.env.user.id
        self.env.cr.execute("""
            SELECT token, api_url FROM isi_pass_config
            WHERE user_id = %s
            LIMIT 1
        """, (current_user_id,))
        result = self.env.cr.fetchone()

        if result:
            token, api_url = result
            return token, api_url
        return None
