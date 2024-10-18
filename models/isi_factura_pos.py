from odoo import models, fields, api, http
from odoo.http import request
import requests
import base64
import logging

_logger = logging.getLogger(__name__)

# State: Desarrollo
# {
# Índice de Código
# 
# Clases
# 1. PosOrder
#    - Atributos
#      - rollo_pdf: Archivo PDF del rollo, almacenado como un campo binario.
#    - Métodos
#      - action_pos_order_paid(): Marca la orden como pagada y genera la factura si es necesario.
#      - _generate_pos_order_invoice(): Genera la factura para la orden POS.
#      - _prepare_invoice(): Prepara los datos necesarios para la creación de la factura.
#      - _get_rollo_pdf(invoice): Descarga el PDF del rollo asociado a la factura.
#      - _check_pdf_content(): Verifica si el contenido del PDF es válido.
# 
# 2. PosSession
#    - Métodos
#      - _pos_ui_models_to_load(): Carga los modelos necesarios en la interfaz de usuario del POS.
#      - _loader_params_pos_order(): Devuelve los parámetros de carga para las órdenes POS.
#      - _get_pos_ui_pos_order(params): Obtiene las órdenes POS basadas en los parámetros dados.
# 
# 3. PosOrderController
#    - Métodos
#      - download_rollo(order_id): Controlador para descargar el PDF del rollo asociado a una orden.
# }
class PosOrder(models.Model):
    # Modelo que representa un pedido en el Punto de Venta (POS).
    _inherit = 'pos.order'

    rollo_pdf = fields.Binary("PDF del Rollo", attachment=True)
    # Campo que almacena el PDF del rollo asociado a la orden, en formato binario.

    def action_pos_order_paid(self):
        # Marca la orden como pagada y genera la factura si es necesario.
        # También se registran detalles del usuario que está marcando la orden como pagada.
        _logger.info("________________________________________")
        _logger.info("Iniciando proceso de facturación")
        _logger.info("________________________________________")

        self.write({'state': 'paid'})

        if self.to_invoice:
            return self._generate_pos_order_invoice()
        
        # Verificamos si el usuario es un empleado
        user = self.env.user
        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        if employee:
            _logger.info(f"Empleado: {employee.name} (ID: {employee.id})")
        else:
            _logger.info(f"Usuario (no empleado): {user.name} (ID: {user.id})")

        return {'type': 'ir.actions.act_window_close'}

    def _generate_pos_order_invoice(self):
        # Genera la factura para la orden POS.
        # Se crean y registran las líneas de factura basadas en los productos de la orden.
        moves = self.env['account.move']
        for order in self:
            try:
                _logger.info(f"Generando factura para la orden POS {order.id}")
                
                # Verificamos si el usuario es un empleado
                user = self.env.user
                employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                if employee:
                    _logger.info(f"Empleado: {employee.name} (ID: {employee.id})")
                else:
                    _logger.info(f"Usuario (no empleado): {user.name} (ID: {user.id})")

                invoice = order._prepare_invoice()
                new_move = moves.sudo().create(invoice)
                order.write({'account_move': new_move.id, 'state': 'invoiced'})
                new_move.sudo().with_context(default_journal_id=new_move.journal_id.id).action_post()
                _logger.info(f"Factura creada: {new_move.id}")

                _logger.info(f"Descargando rollo para la orden POS {order.id}")
                pdf_content = self._get_rollo_pdf(new_move)
                if pdf_content:
                    order.rollo_pdf = base64.b64encode(pdf_content)
                    _logger.info(f"PDF del rollo generado y guardado para la orden {order.id}")
                    if not order._check_pdf_content():
                        _logger.warning(f"El contenido del PDF parece ser inválido para la orden {order.id}")
                else:
                    _logger.warning(f"No se pudo obtener el PDF del rollo para la orden {order.id}")

            except Exception as e:
                _logger.error(f"Error al generar la factura para la orden {order.id}: {str(e)}", exc_info=True)

        return moves

    def _prepare_invoice(self):
        # Prepara los datos necesarios para la creación de la factura.
        # Devuelve un diccionario con la información relevante para la factura.
        return {
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'move_type': 'out_invoice',
            'invoice_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.qty,
                'price_unit': line.price_unit,
                'name': line.product_id.name,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
            }) for line in self.lines],
        }

    def _get_rollo_pdf(self, invoice):
        # Descarga el PDF del rollo asociado a la factura.
        # Argumentos:
        #     invoice: La factura de la cual se descargará el PDF del rollo.
        # Devuelve el contenido del PDF en caso de éxito, o None si hay un error.
        try:
            if not invoice.rollo_url:
                return None

            _logger.info(f"Intentando descargar PDF del rollo. URL: {invoice.rollo_url}")
            response = requests.get(invoice.rollo_url, timeout=10)
            response.raise_for_status()
            
            if response.headers.get('Content-Type') != 'application/pdf':
                _logger.warning(f"Advertencia: El contenido descargado no es un PDF. Tipo de contenido: {response.headers.get('Content-Type')}")
            
            return response.content
        except requests.RequestException as e:
            _logger.error(f"Error al descargar el rollo de la factura {invoice.id}: {str(e)}", exc_info=True)
        except Exception as e:
            _logger.error(f"Error inesperado al obtener el PDF del rollo para la factura {invoice.id}: {str(e)}", exc_info=True)
        return None

    def _check_pdf_content(self):
        # Verifica si el contenido del PDF es válido.
        # Devuelve True si el PDF es válido, de lo contrario False.
        if not self.rollo_pdf:
            _logger.warning(f"rollo_pdf está vacío para la orden: {self.id}")
            return False
        
        pdf_content = base64.b64decode(self.rollo_pdf)
        if not pdf_content:
            _logger.warning(f"PDF decodificado está vacío para la orden: {self.id}")
            return False
        
        if pdf_content[:4] != b'%PDF':
            _logger.warning(f"El contenido no parece ser un PDF válido para la orden: {self.id}")
            return False
        
        _logger.info(f"PDF parece válido para la orden: {self.id}")
        return True

class PosSession(models.Model):
    # Modelo que representa una sesión en el Punto de Venta (POS).
    _inherit = 'pos.session'

    @api.model
    def _pos_ui_models_to_load(self):
        # Carga los modelos necesarios en la interfaz de usuario del POS.
        # Devuelve una lista de modelos a cargar, incluyendo 'pos.order'.
        result = super()._pos_ui_models_to_load()
        result.append('pos.order')
        return result

    def _loader_params_pos_order(self):
        # Devuelve los parámetros de carga para las órdenes POS.
        # Devuelve un diccionario con los parámetros de búsqueda.
        return {'search_params': {'domain': [('session_id', '=', self.id)]}}

    def _get_pos_ui_pos_order(self, params):
        # Obtiene las órdenes POS basadas en los parámetros dados.
        # Argumentos:
        #     params: Parámetros de búsqueda para filtrar las órdenes POS.
        # Devuelve las órdenes POS que coinciden con los parámetros de búsqueda.
        orders = self.env['pos.order'].search(params['search_params']['domain'])
        return orders.read(['rollo_pdf'])

class PosOrderController(http.Controller):
    # Controlador para manejar las solicitudes relacionadas con las órdenes POS.

    @http.route('/pos/web/download_rollo/<int:order_id>', type='http', auth='user')
    def download_rollo(self, order_id, **kwargs):
        # Controlador para descargar el PDF del rollo asociado a una orden.
        # Argumentos:
        #     order_id: ID de la orden para la cual se descargará el PDF del rollo.
        # Devuelve el PDF como una respuesta HTTP o un error si no se puede descargar.
        try:
            order = request.env['pos.order'].sudo().browse(order_id)
            if not order:
                _logger.warning(f"Orden no encontrada: {order_id}")
                return request.not_found()
            
            if not order.rollo_pdf:
                _logger.warning(f"rollo_pdf no encontrado para la orden: {order_id}")
                return request.not_found()
            
            pdf_data = base64.b64decode(order.rollo_pdf)
            return request.make_response(pdf_data, headers=[('Content-Type', 'application/pdf'), ('Content-Disposition', 'attachment; filename="rollo.pdf"')])
        
        except Exception as e:
            _logger.error(f"Error al descargar el rollo para la orden {order_id}: {str(e)}", exc_info=True)
            return request.not_found()
