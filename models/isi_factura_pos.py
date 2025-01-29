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
    
    numero_tarjeta = fields.Char(string="Número de Tarjeta")
    rollo_pdf = fields.Binary("PDF del Rollo", attachment=True)
    cuf = fields.Char("CUF", readonly=True)
    estado_factura = fields.Char("Estado Factura", readonly=True)
    account_move_id = fields.Many2one(
        'account.move', string='Factura Relacionada')

    @api.model
    def updateCardNumber(self, order_id, card_number):
        order = self.browse(order_id)
        if order:
            order.numero_tarjeta = card_number
            return True
        return False
    
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

        if not self.to_invoice:
            return

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

            # Enviar la respuesta al bus de Odoo
            self.env['bus.bus']._sendone(
                self.env.user.partner_id, 
                'api_response_channel', 
                {
                    'type': 'api_response',
                    'payload': response.json()
                }
            )
        

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
                _logger.warning(
                    f"PDF decodificado está vacío para la orden: {self.id}")
                return False

            if pdf_content[:4] != b'%PDF':
                _logger.warning(
                    f"El contenido no parece ser un PDF válido para la orden: {self.id}")
                return False

            _logger.info(f"PDF válido para la orden: {self.id}")
            return True
        except Exception as e:
            _logger.error(f"Error al verificar el PDF para la orden {self.id}: {str(e)}")
            return False

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

        actividad_economica = self.lines[0].product_id.codigo_producto_homologado.split(' - ')[0]

        numero_tarjeta = None
        codigo_metodo_pago = 1

        if self.payment_ids:
            payment = self.payment_ids[0]
            try:
                codigo_metodo_pago = int(
                    payment.payment_method_id.metodo_pago_sin)
            except:
                _logger.warning(
                    "No se pudo obtener método de pago SIN, usando valor por defecto")

            if codigo_metodo_pago == 2:
                numero_tarjeta = self.numero_tarjeta or ''

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
                'detalleExtra': '',
                'detalle': detalle
            }
        }

    

    def action_pos_order_paid(self):
        print("\n----------------------------------------")
        print("Iniciando proceso de facturación")
        print("----------------------------------------")

        
        # Si no es para facturar, seguimos el comportamiento estándar de Odoo
        if not self.to_invoice:
            return super(PosOrder, self).action_pos_order_paid()

        try:
            # Preparar datos de la factura
            invoice_data = self._prepare_invoice_data()

            print("\n----------------------------------------")
            print("Datos de la factura:")
            print(json.dumps(invoice_data, indent=2))
            print("----------------------------------------")
            # Enviar a la API
            response = self._send_invoice_to_api(invoice_data)

            # Verificar si hay errores en la respuesta
            if 'errors' in response:
                error_message = response['errors'][0]['message']
                print("\n----------------------------------------")
                print(f"Error en la API: {error_message}")
                print("La orden NO será marcada como pagada")
                print("----------------------------------------")
                
                # No marcamos la orden como pagada y lanzamos el error
                raise ValueError(f"Error en la respuesta de la API: {error_message}")

            if response.get('data', {}).get('facturaCompraVentaCreate'):
                result = response['data']['facturaCompraVentaCreate']

                # Preparar y crear/actualizar account.move
                account_move_data = self._prepare_account_move_data(response)
                account_move = self._create_or_update_account_move(account_move_data)

                # Guardar el PDF del rollo si está disponible
                if result.get('representacionGrafica', {}).get('rollo'):
                    rollo_url = result['representacionGrafica']['rollo']
                    # try:
                    #     # Descargar el PDF desde la URL
                    #     pdf_response = requests.get(rollo_url)
                    #     if pdf_response.status_code == 200:
                    #         # Convertir el contenido a base64
                    #         pdf_base64 = base64.b64encode(pdf_response.content).decode('utf-8')
                    #         self.write({
                    #             'rollo_pdf': pdf_base64,
                    #             'cuf': result.get('cuf'),
                    #             'estado_factura': result.get('state')
                    #         })
                    #         _logger.info(f"PDF del rollo descargado y guardado exitosamente para la orden {self.id}")
                    #     else:
                    #         _logger.warning(f"No se pudo descargar el PDF del rollo para la orden {self.id}. Status code: {pdf_response.status_code}")
                    # except Exception as e:
                    #     _logger.error(f"Error al descargar el PDF del rollo para la orden {self.id}: {str(e)}")

                print("\n----------------------------------------")
                print("Factura procesada exitosamente")
                print(f"CUF: {result.get('cuf')}")
                print(f"Estado: {result.get('state')}")
                print("----------------------------------------")

                # Solo marcamos como pagado si todo el proceso fue exitoso
                self.write({'state': 'paid'})
                print("\nOrden marcada como pagada")
                print("----------------------------------------\n")
                
                return True

            else:
                error_msg = "Respuesta de API inválida"
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
            print("La orden NO será marcada como pagada")
            print("----------------------------------------")
            raise

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
    



    def _create_or_update_account_move(self, invoice_data):
        """Crea o actualiza el registro en account.move"""
        AccountMove = self.env['account.move']

        # Si ya existe una factura asociada, la actualizamos
        if self.account_move_id:
            self.account_move_id.write(invoice_data)
            return self.account_move_id

        # Aseguramos que el estado inicial sea 'draft'
        invoice_data['state'] = 'draft'
        
        # Si no existe, creamos una nueva
        invoice_data.update({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.date_order.date(),
            'invoice_origin': self.name,
            'pos_order_ids': [(4, self.id)],
        })

        new_move = AccountMove.create(invoice_data)
        
        # Después de crear la factura, la publicamos
        try:
            new_move.action_post()
        except Exception as e:
            _logger.error(f"Error al publicar la factura: {str(e)}")
            raise

        self.write({'account_move_id': new_move.id})
        return new_move

    def _prepare_account_move_data(self, response_data):

        if not self.to_invoice:
            return
            
        """Prepara los datos completos para crear o actualizar el account.move, incluyendo líneas de productos"""
        result = response_data.get('data', {}).get('facturaCompraVentaCreate', {})
        representacion_grafica = result.get('representacionGrafica', {})
        
        
        
        # Preparar líneas de factura
        invoice_lines = []
        for line in self.lines:
            invoice_line_vals = {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.qty,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'product_uom_id': line.product_id.uom_id.id,
                'tax_ids': [(6, 0, line.tax_ids_after_fiscal_position.ids)],
                'display_type': 'product',
                'sequence': line.id,
                # Campos adicionales específicos del producto
            }
            invoice_lines.append((0, 0, invoice_line_vals))

        return {
            # Campos de sistema con valores específicos
            'state': 'draft',  # Cambiado a 'draft' en lugar de 'posted'
            'payment_state': 'not_paid',  # Inicialmente no pagado
            'move_type': 'out_invoice',
            'invoice_origin': self.name,
            'journal_id': self.session_id.config_id.invoice_journal_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'invoice_user_id': self.env.user.id,
            'invoice_date': self.date_order.date(),
            'date': self.date_order.date(),
            'invoice_date_due': self.date_order.date(),
            
            # Campos de montos
            'amount_untaxed': self.amount_total - self.amount_tax,
            'amount_tax': self.amount_tax,
            'amount_total': self.amount_total,
            'amount_residual': self.amount_total,  # Inicialmente el monto total
            'amount_untaxed_signed': self.amount_total - self.amount_tax,
            'amount_tax_signed': self.amount_tax,
            'amount_total_signed': self.amount_total,
            'amount_residual_signed': self.amount_total,  # Inicialmente el monto total

            # Campos personalizados de la facturación
            'razon_social': self.partner_id.razon_social or 'Sin Razón Social',
            'codigo_tipo_documento_identidad': self.partner_id.codigo_tipo_documento_identidad,
            'phone': self.partner_id.phone,
            'email': self.partner_id.email,
            'codigo_metodo_pago': self.payment_ids and self.payment_ids[0].payment_method_id.metodo_pago_sin or '1',

            # Campos específicos de la respuesta API
            'cuf': result.get('cuf'),
            'api_invoice_id': result.get('_id'),
            'api_invoice_state': result.get('state'),
            'pdf_url': representacion_grafica.get('pdf'),
            'sin_url': representacion_grafica.get('sin'),
            'rollo_url': representacion_grafica.get('rollo'),
            'xml_url': representacion_grafica.get('xml'),
            'numero_tarjeta': self.payment_ids and self.payment_ids[0].payment_method_id.metodo_pago_sin == '2' and self.numero_tarjeta or False,
            # Campos adicionales de control
            'permitir_nit_invalido': False,
            'additional_discount': 0,
            'gift_card_amount': 0,
            'custom_subtotal': self.amount_total - self.amount_tax,
            'custom_total': self.amount_total,
            
            # Líneas de factura
            'invoice_line_ids': invoice_lines,
            'payment_state': 'paid',
            'state': 'posted',
            # colocamos como publicado para que no se pueda modificar y tambien pagado
            'payment_state': 'paid',

            
        }


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
