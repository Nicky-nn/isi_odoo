import random
from odoo import models, fields, api, http
from odoo.http import request
import requests
import base64
import logging
import json

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    rollo_pdf = fields.Binary("PDF del Rollo", attachment=True)
    cuf = fields.Char("CUF", readonly=True)
    estado_factura = fields.Char("Estado Factura", readonly=True)

    def _prepare_invoice_data(self):
        """Prepara los datos para la factura en el formato requerido por la API"""
        cliente = {}
        if self.partner_id:
            cliente = {
                'razonSocial': self.partner_id.razon_social or 'Sin Razón Social',
                'numeroDocumento': self.partner_id.vat or '',
                'email': self.partner_id.email or '',
                'codigoTipoDocumentoIdentidad': int(self.partner_id.codigo_tipo_documento_identidad or 1),
                'complemento': self.partner_id.complemento or ''
            }
        else:
            cliente = {
                'razonSocial': 'Sin Razón Social',
                'numeroDocumento': '',
                'email': '',
                'codigoTipoDocumentoIdentidad': 1
            }

        detalle = []
        codigos_producto_sin = []

        for line in self.lines:
            try:
                item_detalle = {
                    'codigoProductoSin': line.product_id.codigo_producto_homologado.split(' - ')[1] or '',
                    'codigoProducto': line.product_id.default_code or '',
                    'descripcion': line.product_id.name,
                    'cantidad': line.qty,
                    'unidadMedida': int(line.product_id.codigo_unidad_medida.split(' - ')[0]) or '',
                    'precioUnitario': line.price_unit,
                    'montoDescuento': line.price_unit * line.qty * line.discount / 100,
                    'detalleExtra': ''
                }
                detalle.append(item_detalle)
                codigos_producto_sin.append(item_detalle['codigoProductoSin'])

            except Exception as e:
                _logger.error(f"Error procesando producto: {str(e)}")

        actividad_economica = "620000"

        numero_tarjeta = None
        codigo_metodo_pago = 1

        if self.payment_ids:
            payment = self.payment_ids[0]
            try:
                codigo_metodo_pago = int(payment.payment_method_id.metodo_pago_sin)
            except:
                _logger.warning("No se pudo obtener método de pago SIN, usando valor por defecto")

            if codigo_metodo_pago == 2:
                numero_tarjeta = "00000000"

        return {
            'entidad': {
                'codigoSucursal': 0,
                'codigoPuntoVenta': 0
            },
            'input': {
                'cliente': cliente,
                'codigoExcepcion': 1,
                'actividadEconomica': actividad_economica,
                'codigoMetodoPago': codigo_metodo_pago,
                'numeroTarjeta': numero_tarjeta,
                'descuentoAdicional': 0,
                'codigoMoneda': 1,
                'tipoCambio': 1,
                'detalleExtra': '<p><strong>Detalle extra</strong></p>',
                'detalle': detalle
            }
        }

    def _send_invoice_to_api(self, invoice_data):
        """Envía los datos de la factura a la API"""
        token, api_url = self._get_api_config()
        
        if not token or not api_url:
            raise ValueError("Configuración de API no encontrada")

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        query = """
        mutation FCV_REGISTRO_ONLINE($entidad: EntidadParamsInput, $input: FacturaCompraVentaInput!) {
            facturaCompraVentaCreate(entidad: $entidad, input: $input) {
                _id
                cafc
                cuf
                razonSocialEmisor
                representacionGrafica {
                    pdf
                    rollo
                    sin
                    xml
                }
                state
                updatedAt
                usuario
                usucre
                usumod
            }
        }
        """

        try:
            response = requests.post(
                api_url,
                json={
                    'query': query,
                    'variables': {
                        'input': invoice_data['input']
                    }
                },
                headers=headers
            )
            print("\n----------------------------------------")
            print("Respuesta de la API 1:")
            print(json.dumps(response.json(), indent=2))
            print("----------------------------------------")
            response.raise_for_status()

            # Parsear los datos de la respuesta
            data = response.json()

            # Verificar errores en la respuesta y registrarlos
            if 'errors' in data:
                error_message = json.dumps(data['errors'], indent=2)
                self._log_api_error(f"Error al enviar la factura a la API: {error_message}")
                
                # Mostrar en consola el error detallado
                print("\n----------------------------------------")
                print("Error en la respuesta de la API:")
                print(json.dumps(data, indent=2))
                print("----------------------------------------")

                raise ValueError(f"Error en la respuesta de la API: {error_message}")

            return data

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error en la llamada a la API: {str(e)}")
            
            # Mostrar en consola los detalles de la excepción
            print("\n----------------------------------------")
            print("Error en la llamada a la API:")
            print(f"Detalles del error: {str(e)}")
            print("----------------------------------------")

            raise

    def _check_pdf_content(self):
        """Verifica si el contenido del PDF es válido"""
        if not self.rollo_pdf:
            _logger.warning(f"rollo_pdf está vacío para la orden: {self.id}")
            return False
        
        try:
            pdf_content = base64.b64decode(self.rollo_pdf)
            if not pdf_content:
                _logger.warning(f"PDF decodificado está vacío para la orden: {self.id}")
                return False
            
            if pdf_content[:4] != b'%PDF':
                _logger.warning(f"El contenido no parece ser un PDF válido para la orden: {self.id}")
                return False
            
            _logger.info(f"PDF válido para la orden: {self.id}")
            return True
        except Exception as e:
            _logger.error(f"Error al verificar el PDF para la orden {self.id}: {str(e)}")
            return False

    def action_pos_order_paid(self):
        print("\n----------------------------------------")
        print("Iniciando proceso de facturación")
        print("----------------------------------------")

        # Preparar datos de la factura
        invoice_data = self._prepare_invoice_data()
        
        print("\n----------------------------------------")
        print("Datos de la factura preparados:")
        print(json.dumps(invoice_data, indent=2))
        print("----------------------------------------")

        try:
            # Enviar a la API
            response = self._send_invoice_to_api(invoice_data)
            
            if response.get('data', {}).get('facturaCompraVentaCreate'):
                result = response['data']['facturaCompraVentaCreate']
                
                # Guardar el PDF del rollo si está disponible
                if result.get('representacionGrafica', {}).get('rollo'):
                    rollo_url = result['representacionGrafica']['rollo']
                    try:
                        # Descargar el PDF desde la URL
                        pdf_response = requests.get(rollo_url)
                        if pdf_response.status_code == 200:
                            # Convertir el contenido a base64
                            pdf_base64 = base64.b64encode(pdf_response.content).decode('utf-8')
                            self.write({
                                'rollo_pdf': pdf_base64,
                                'cuf': result.get('cuf'),
                                'estado_factura': result.get('state')
                            })
                            _logger.info(f"PDF del rollo descargado y guardado exitosamente para la orden {self.id}")
                        else:
                            _logger.warning(f"No se pudo descargar el PDF del rollo para la orden {self.id}. Status code: {pdf_response.status_code}")
                    except Exception as e:
                        _logger.error(f"Error al descargar el PDF del rollo para la orden {self.id}: {str(e)}")

                print("\n----------------------------------------")
                print("Factura procesada exitosamente")
                print(f"CUF: {result.get('cuf')}")
                print(f"Estado: {result.get('state')}")
                print("----------------------------------------")
            else:
                error_msg = response.get('errors', [{'message': 'Error desconocido'}])[0]['message']
                print("\n----------------------------------------")
                print("Error desconocido al procesar la factura:")
                print(json.dumps(response, indent=2))
                print("----------------------------------------")
                raise ValueError(f"Error en la respuesta de la API: {error_msg}")

        except Exception as e:
            _logger.error(f"Error en el proceso de facturación: {str(e)}")
            print("\n----------------------------------------")
            print("Error en el proceso de facturación:")
            print(f"Detalles del error: {str(e)}")
            print("----------------------------------------")
            raise

        # Marcar como pagado
        self.write({'state': 'paid'})
        
        print("\nOrden marcada como pagada")
        print("----------------------------------------\n")
        
        return True
    

    
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


class PosOrderController(http.Controller):
    @http.route('/pos/web/download_rollo/<int:order_id>', type='http', auth='user')
    def download_rollo(self, order_id, **kwargs):
        """Controlador para descargar el PDF del rollo"""
        try:
            order = request.env['pos.order'].sudo().browse(order_id)
            if not order or not order.rollo_pdf:
                _logger.warning(f"PDF del rollo no encontrado para la orden: {order_id}")
                return request.not_found()

            if not order._check_pdf_content():
                _logger.warning(f"El contenido del PDF no es válido para la orden: {order_id}")
                return request.not_found()

            pdf_data = base64.b64decode(order.rollo_pdf)
            filename = f'rollo_{order.name}_{order.date_order.strftime("%Y%m%d")}.pdf'
            
            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
                ('Content-Length', len(pdf_data))
            ]
            
            return request.make_response(pdf_data, headers=headers)
            
        except Exception as e:
            _logger.error(f"Error al descargar el rollo para la orden {order_id}: {str(e)}", exc_info=True)
            return request.not_found()