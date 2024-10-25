import requests
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class POSPaymentMethod(models.Model):
    # La clase POSPaymentMethod extiende el modelo 'pos.paid.method' para incluir funcionalidad adicional para la integración con una API externa para recuperar métodos de pago.

    # Atributos:
    # metodo_pago_sin (campos.Selección): Un campo de selección para almacenar el método de pago del SIN.

    # Métodos:
    # _get_api_config():
    # Recupera la configuración de API (token y URL) para el usuario actual de la base de datos.

    # get_paid_methods_from_api():
    # Obtiene métodos de pago de una API externa utilizando el token y la URL almacenados.
    # Devuelve una lista de tuplas que contienen el código y la descripción del método de pago.

    # _get_paid_method_selection():
    # Recupera los métodos de pago de la API externa y los devuelve como una lista de selección.
    # Si no se recupera ningún método, se registra una advertencia y se agrega una opción vacía a la lista.
    _inherit = 'pos.payment.method'

    metodo_pago_sin = fields.Selection(
        selection='_get_payment_method_selection',
        string='Método de Pago SIN',
        required=False,
        default=False
    )

    facturacion_obligatoria = fields.Boolean(
        string='Facturación Obligatoria',
        default=False,
        help="Si está marcado, las ventas con este método de pago requerirán facturación obligatoria"
    )

    @api.model
    def _get_api_config(self):
        self.env.cr.execute("""
            SELECT token, api_url 
            FROM isi_pass_config 
            WHERE user_id = %s 
            LIMIT 1
        """, (self.env.user.id,))
        result = self.env.cr.fetchone()
        return result if result else (None, None)

    @api.model
    def get_payment_methods_from_api(self):
        token, api_url = self._get_api_config()
        if not token or not api_url:
            _logger.error("No se pudo obtener el token o la URL de la API")
            return []

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        query = """
        query tipoMetodoPago {
            sinTipoMetodoPago {
                codigoClasificador
                descripcion
            }
        }
        """

        try:
            response = requests.post(
                api_url, json={'query': query}, headers=headers)
            response.raise_for_status()
            data = response.json()
            return [(str(method['codigoClasificador']), method['descripcion'])
                    for method in data['data']['sinTipoMetodoPago']]
        except requests.RequestException as e:
            _logger.error(
                f"Error al obtener métodos de pago de la API: {str(e)}")
            return []

    @api.model
    def _get_payment_method_selection(self):
        methods = self.get_payment_methods_from_api()
        if not methods:
            _logger.warning(
                "No se pudieron obtener métodos de pago de la API. Solo estará disponible la opción vacía.")
        return methods
