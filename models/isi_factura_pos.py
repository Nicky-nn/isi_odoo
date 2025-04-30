# -*- coding: utf-8 -*-
import base64
import random
import requests
import json
import logging

from odoo import models, fields, api, _
from odoo import http
from odoo.exceptions import UserError # Importante para notificar errores al frontend
from odoo.http import request

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    # --- Campos (Sin cambios) ---
    temporary_card_number = fields.Char(
        string="Número de Tarjeta Temporal", readonly=True, copy=False,
        help="Número de tarjeta ingresado en el POS para pagos con tarjeta."
    )
    invoice_api_response = fields.Text(string="Respuesta API Facturación", readonly=True, copy=False)
    invoice_pdf_url = fields.Char(string="URL PDF Factura", readonly=True, copy=False)
    invoice_xml_url = fields.Char(string="URL XML Factura", readonly=True, copy=False)
    invoice_sin_url = fields.Char(string="URL SIN Factura", readonly=True, copy=False)
    invoice_rollo_url = fields.Char(string="URL Rollo Factura", readonly=True, copy=False)

    # --- _order_fields (Sin cambios) ---
    @api.model
    def _order_fields(self, ui_order):
        fields_to_include = super(PosOrder, self)._order_fields(ui_order)
        fields_to_include['temporary_card_number'] = ui_order.get('temporary_card_number')
        return fields_to_include

    # --- Métodos Configuración API (Sin cambios) ---
    @api.model
    def _get_api_token_for_user(self, user_id):
        self.env.cr.execute("SELECT token FROM isi_pass_config WHERE user_id = %s LIMIT 1", (user_id,))
        result = self.env.cr.fetchone()
        if not result:
            _logger.warning(f"No se encontró token de API para el usuario ID: {user_id}")
            return None
        return result[0]

    @api.model
    def _get_api_url(self, user_id):
        self.env.cr.execute("SELECT api_url FROM isi_pass_config WHERE user_id = %s LIMIT 1", (user_id,))
        result = self.env.cr.fetchone()
        if not result:
            _logger.warning(f"No se encontró URL de API para el usuario ID: {user_id}")
            return None
        return result[0]

    def _get_api_config(self, user_id, column_name):
        allowed = {'sucursal_codigo', 'punto_venta_codigo'}
        if column_name not in allowed:
            _logger.error(f"Columna no permitida solicitada en _get_api_config: {column_name}")
            raise ValueError(f"Columna no permitida: {column_name}") # Error de programación

        self.env.cr.execute(f"SELECT {column_name} FROM isi_pass_config WHERE user_id = %s LIMIT 1", (user_id,))
        row = self.env.cr.fetchone()
        if not row:
            _logger.warning(f"No se encontró {column_name} para el usuario ID: {user_id}")
            return None
        try:
            # Intentar convertir a entero, devolver None si falla o es None
            return int(row[0]) if row[0] is not None else None
        except (ValueError, TypeError):
             _logger.warning(f"Valor no numérico para {column_name} (user {user_id}): {row[0]}")
             return None

    # --- Método _process_order Modificado ---
    @api.model
    def _process_order(self, order_data, draft, existing_order):
        # 1. Procesamiento original para crear/actualizar la orden
        order_id = super(PosOrder, self)._process_order(order_data, draft, existing_order)
        order = self.browse(order_id)
        if not order:
            _logger.error(f"_process_order: No se pudo encontrar la orden con ID {order_id} después de super()._process_order.")
            raise UserError(_("No se pudo procesar la orden correctamente (ID no encontrado)."))

        # --- Debug: Información de Orden y Cliente ---
        print("\n----------------------------------------")
        print(f"PROCESANDO ORDEN POS: {order.name}")
        print("----------------------------------------")
        print("CLIENTE:")
        if order.partner_id:
            partner = order.partner_id
            print(f"  Razon Social: {partner.name}")
            print(f"  codigoTipoDocumentoIdentidad: {int(getattr(partner, 'codigo_tipo_documento_identidad', 0))}")
            print(f"  codigoCliente (NIT/CI): {partner.vat or 'No especificado'}")
            print(f"  Email: {partner.email or 'No especificado'}")
            print(f"  Complemento: {getattr(partner, 'complemento', 'No especificado')}")
        else:
            print("  Cliente: Consumidor Final / No especificado")

        print("\nPRODUCTOS:")
        for i, line in enumerate(order.lines, 1):
            print(f"  {i}. {line.product_id.name}")
            print(f"     Cantidad: {line.qty}")
            print(f"     Precio unitario: {line.price_unit}")
            if line.discount:
                descuento_monto = (line.price_unit * line.qty) * (line.discount / 100)
                print(f"     Descuento: {descuento_monto:.2f}")
            print(f"     Subtotal: {line.price_subtotal}")

        print("\nMÉTODOS DE PAGO:")
        if order.payment_ids:
            for payment in order.payment_ids:
                method = payment.payment_method_id
                print(f"  Método: {method.name}")
                print(f"  Método SIN: {getattr(method, 'metodo_pago_sin', 'No Definido')}")
                if order.temporary_card_number and 'tarjeta' in method.name.lower():
                    print(f"  Número Tarjeta (Temporal): {order.temporary_card_number}")
                print(f"  Monto: {payment.amount}")
        else:
            print("  No se registraron pagos (esto sería inusual aquí)")

        print("\nFACTURACIÓN:")
        print(f"  Se factura: {'Sí' if order.to_invoice else 'No'}")

        print("\nTOTALES:")
        print(f"  Subtotal (antes de imp.): {order.amount_total - order.amount_tax}")
        print(f"  Impuestos: {order.amount_tax}")
        print(f"  Total: {order.amount_total}")
        print("----------------------------------------")

        print(f"Orden Odoo Creada/Actualizada: {order.name} [ID: {order_id}]")
        # 3. Lógica de Facturación API (SI la orden lo requiere)
        if order.to_invoice:
            print("\n----------------------------------------")
            print(f"--- INICIO Facturación API para: {order.name} (Dentro de _process_order) ---")

            # Obtener configuración de API
            current_user_id = self.env.user.id # Usuario que está procesando
            token = order._get_api_token_for_user(current_user_id)
            api_url = order._get_api_url(current_user_id)
            codigo_sucursal    = order._get_api_config(current_user_id, 'sucursal_codigo')
            codigo_punto_venta = order._get_api_config(current_user_id, 'punto_venta_codigo')

            # Validar configuración esencial Y Lanzar UserError si falta
            if not token or not api_url or codigo_sucursal is None or codigo_punto_venta is None:
                error_message = "Error de Configuración API: Falta Token, URL, Sucursal o Punto Venta."
                print(f"ERROR: {error_message}")
                _logger.error(f"{error_message} (Usr: {current_user_id}, Orden: {order.name})")
                order.write({'invoice_api_response': error_message}) # Guardar error para referencia
                # Lanzar UserError detiene _process_order y falla la llamada RPC original
                raise UserError(error_message)

            # --- Preparar datos para la API ---
            # (Toda la lógica para preparar cliente_data, detalle_factura,
            #  metodo_pago, actividad_economica, factura_input, graphql_variables
            #  permanece igual que en tu versión de action_pos_order_paid)
            # ...
            # Datos del cliente
            if order.partner_id:
                partner = order.partner_id
                try: cod_tipo_doc_cliente = int(getattr(partner, 'codigo_tipo_documento_identidad', 5))
                except (ValueError, TypeError): cod_tipo_doc_cliente = 5
                cliente_data = {
                    "razonSocial": getattr(partner, 'razon_social', partner.name) or "Sin Nombre",
                    "numeroDocumento": partner.vat or "",
                    "complemento": getattr(partner, 'complemento', None) or None,
                    "email": partner.email or "sin_correo@dominio.com",
                    "codigoTipoDocumentoIdentidad": cod_tipo_doc_cliente
                }
            else:
                cliente_data = {
                    "razonSocial": "Sin Registro", "numeroDocumento": "0", "complemento": None,
                    "email": "sin_correo@dominio.com", "codigoTipoDocumentoIdentidad": 5
                }
            # print(" Cliente:", cliente_data) # Descomentar si es necesario

            # Detalles de los productos
            detalle_factura = []

            for line in order.lines:
                if not line.product_id:
                    continue

                producto = line.product_id
                unidad_medida = getattr(producto.uom_id, 'unidad_medida_sin', 1)
                try:
                    unidad_medida_api_val = int(unidad_medida)
                except (ValueError, TypeError):
                    unidad_medida_api_val = 1

                codigo_sin = "codigoProductoSin esta mal"
                if producto.codigo_producto_homologado:
                    partes = producto.codigo_producto_homologado.split(' - ')
                    if len(partes) > 1:
                        codigo_sin = partes[1]

                monto_descuento = round((line.price_unit * line.qty) * (line.discount / 100), 2)

                detalle_factura.append({
                    "codigoProductoSin": codigo_sin,
                    "codigoProducto": producto.default_code or f"PROD-{producto.id}",
                    "descripcion": producto.name or "N/A",
                    "cantidad": line.qty,
                    "unidadMedida": unidad_medida_api_val,
                    "precioUnitario": line.price_unit,
                    "montoDescuento": monto_descuento,
                })

            # print(" Detalle:", detalle_factura) # Descomentar si es necesario

            # Método de pago y número de tarjeta
            codigo_metodo_pago_api = 1; numero_tarjeta_api = None
            if order.payment_ids:
                first_payment = order.payment_ids[0]; payment_method = first_payment.payment_method_id
                try: codigo_metodo_pago_api = int(getattr(payment_method, 'metodo_pago_sin', 1))
                except (ValueError, TypeError): codigo_metodo_pago_api = 1
                if str(codigo_metodo_pago_api) == '2' and order.temporary_card_number:
                    numero_tarjeta_api = order.temporary_card_number
                if str(codigo_metodo_pago_api) != '2': numero_tarjeta_api = None
            # print(f" Método Pago: {codigo_metodo_pago_api}, Tarjeta: {'Sí' if numero_tarjeta_api else 'No'}") # Descomentar

            # Actividad económica
            actividades_economicas = set()
            for line in order.lines:
                if line.product_id and line.product_id.codigo_producto_homologado:
                    parts = line.product_id.codigo_producto_homologado.split(' - ')
                    if len(parts) > 0 and parts[0].isdigit(): actividades_economicas.add(parts[0])
            actividad_economica = random.choice(list(actividades_economicas)) if actividades_economicas else "620000"
            # print(f" Actividad Económica: {actividad_economica}") # Descomentar si es necesario

            # Input para GraphQL
            factura_input = {
                "cliente": cliente_data, "codigoExcepcion": 0,
                "actividadEconomica": actividad_economica, "codigoMetodoPago": codigo_metodo_pago_api,
                "numeroTarjeta": numero_tarjeta_api, "descuentoAdicional": 0,
                "codigoMoneda": 1, "tipoCambio": 1, "detalle": detalle_factura
            }
            # print(" Input GraphQL:", json.dumps(factura_input, indent=2)) # Descomentar

            # Variables GraphQL
            graphql_variables = {
                "entidad": {"codigoSucursal": int(codigo_sucursal), "codigoPuntoVenta": int(codigo_punto_venta)},
                "input": factura_input
            }
            # print(" Variables GraphQL:", json.dumps(graphql_variables, indent=2)) # Descomentar

            # Mutación GraphQL (Corregida, sin state, message, etc.)
            graphql_mutation = """
            mutation FCV_REGISTRO_ONLINE($entidad: EntidadParamsInput!, $input: FacturaCompraVentaInput!) {
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
                }
            }
            """
            # print(" Mutación GraphQL:", graphql_mutation) # Descomentar si necesitas verla

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            print("\n--- ENVIANDO DATOS A API DE FACTURACIÓN ---")
            # Clona las variables para no modificar el original al ocultar el token para el print
            variables_copy_for_print = graphql_variables.copy()
            # No imprimimos el token directamente en consola por seguridad, aunque sí lo usamos
            print(f"URL: {api_url}")
            # print(f"Headers: {headers}") # No imprimir headers completos por el token
            print("Variables (Payload):")
            print(json.dumps(variables_copy_for_print, indent=2))
            print("--- FIN DATOS A ENVIAR ---")

            # --- Realizar la llamada a la API y Manejar Respuesta/Errores ---
            try:
                response = requests.post(
                    api_url,
                    headers=headers,
                    json={'query': graphql_mutation, 'variables': graphql_variables},
                    timeout=45 # Puedes ajustar el timeout
                )
                response_text = response.text
                # Guardar respuesta en Odoo (truncada si es larga)
                log_response = response_text[:1500] + ('...' if len(response_text) > 1500 else '')
                order.write({'invoice_api_response': log_response})

                # Verificar errores HTTP (4xx, 5xx) PRIMERO
                response.raise_for_status() # Lanza HTTPError si no es 2xx

                # Si HTTP OK (2xx), procesar JSON
                api_response_json = response.json()
                print("\n--- RESPUESTA DE LA API ---")
                print(json.dumps(api_response_json, indent=2))
                print("--- FIN RESPUESTA API ---")


                # Analizar respuesta GraphQL
                if 'errors' in api_response_json and api_response_json['errors']:
                    # ERROR GraphQL: Extraer mensaje(s) y lanzar UserError
                    error_messages = [e.get('message', 'Error GraphQL desconocido')
                                      for e in api_response_json['errors']]
                    specific_error_message = "; ".join(error_messages)
                    print(f"ERROR GraphQL API: {specific_error_message}")
                    _logger.error(f"Error GraphQL API para orden {order.name}: {specific_error_message}")
                    # Lanzar UserError CON EL MENSAJE EXACTO DE LA API
                    raise UserError(specific_error_message)

                elif 'data' in api_response_json and api_response_json['data'].get('facturaCompraVentaCreate'):
                    api_result_data = api_response_json['data']['facturaCompraVentaCreate']
                    
                    if api_result_data and api_result_data.get('representacionGrafica'):
                        representacion_grafica = api_result_data.get('representacionGrafica', {})
                        
                        # Guardar URLs en la orden POS
                        order.write({
                            'invoice_pdf_url': representacion_grafica.get('pdf'),
                            'invoice_xml_url': representacion_grafica.get('xml'),
                            'invoice_sin_url': representacion_grafica.get('sin'),
                            'invoice_rollo_url': representacion_grafica.get('rollo'),
                        })
                        
                        # Preparar datos para la factura Odoo
                        move_vals = order._prepare_account_move_data(api_response_json)
                        
                        # Verificar si ya existe una factura asociada
                        if order.account_move:
                            order._update_invoice_with_api_data(api_result_data)
                            # Actualizar la factura existente con los datos de la API
                            print(f"Actualizando factura existente ID: {order.account_move.id} con datos de la API")
                            
                            # Extraer solo los campos relevantes de la API para actualizar
                            api_update_vals = {
                                'cuf': api_result_data.get('cuf'),
                                'api_invoice_id': api_result_data.get('_id'),
                                'pdf_url': representacion_grafica.get('pdf'),
                                'sin_url': representacion_grafica.get('sin'),
                                'rollo_url': representacion_grafica.get('rollo'),
                                'xml_url': representacion_grafica.get('xml'),
                                # Otros campos importantes de la respuesta...
                            }
                            # Actualizar solo con los valores de la API, sin tocar líneas o estructura
                            order.account_move.sudo().write(api_update_vals)
                            print(f"Factura ID: {order.account_move.id} actualizada con datos de la API")
                        else:
                            # Si no hay factura, crearla con todos los datos
                            try:
                                invoice = self.env['account.move'].with_context(default_move_type='out_invoice').sudo().create(move_vals)
                                print(f"Factura Odoo creada con ID: {invoice.id} para la orden POS {order.id}")
                                
                                # Vincular la factura con la orden POS
                                order.sudo().write({'account_move': invoice.id})
                                
                                # Si necesitas validar la factura
                                if invoice.state == 'draft':
                                    invoice.sudo().action_post()
                                    print(f"Factura Odoo ID: {invoice.id} publicada.")
                            except Exception as e_invoice:
                                error_msg = f"Error al crear factura: {e_invoice}"
                                print(f"ERROR: {error_msg}")
                                _logger.error(error_msg)
                                raise UserError(error_msg)

                    else:
                        # Respuesta 'data' OK pero incompleta (ej: sin representacionGrafica)
                        error_detail = "Respuesta API OK pero incompleta (sin datos gráficos)."
                        print(f"ERROR: {error_detail}")
                        _logger.warning(f"{error_detail} para orden {order.name}. Respuesta: {log_response}")
                        # Lanzar UserError porque no se completó como se esperaba
                        raise UserError(error_detail)
                else:
                    # Respuesta JSON inesperada (ni 'errors' ni 'data' válidos)
                    error_detail = "Respuesta API inesperada (formato JSON no reconocido)."
                    print(f"ERROR: {error_detail}")
                    _logger.error(f"{error_detail} para orden {order.name}. Respuesta: {log_response}")
                    # Lanzar UserError
                    raise UserError(error_detail)

            # --- Manejo de Excepciones (Red, HTTP, etc.) ---
            except requests.exceptions.Timeout as e:
                error_message = "Error de Conexión: Timeout al conectar con la API."
                print(f"ERROR API: Timeout - {e}")
                _logger.error(f"{error_message} (Orden: {order.name}): {e}")
                order.write({'invoice_api_response': f"{error_message} - {e}"})
                # Lanzar UserError
                raise UserError(error_message)

            except requests.exceptions.RequestException as e:
                # Errores HTTP (4xx, 5xx) u otros de conexión
                http_error_msg = str(e)
                error_message = f"Error de Conexión/HTTP: {http_error_msg}"
                final_error_message = error_message # Default
                # Intentar obtener mensaje específico si la respuesta del error es JSON
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_json = e.response.json()
                        if 'errors' in error_json and error_json['errors']:
                             specific_api_error = "; ".join([err.get('message', '') for err in error_json['errors'] if err.get('message')])
                             if specific_api_error: final_error_message = specific_api_error
                        elif 'message' in error_json and error_json['message']:
                             final_error_message = error_json['message']
                    except json.JSONDecodeError:
                        pass # No era JSON, usar el error HTTP original

                print(f"ERROR API Conexión/HTTP: {final_error_message}")
                _logger.error(f"Error Conexión/HTTP API (Orden: {order.name}): {final_error_message}")
                order.write({'invoice_api_response': final_error_message})
                # Lanzar UserError (con mensaje específico si se pudo extraer)
                raise UserError(final_error_message)

            except UserError:
                 # Relanzar UserErrors ya generados (GraphQL, lógica, etc.)
                 # para que Odoo los maneje y no caigan en el 'except Exception'
                 print(f"Relanzando UserError para orden {order.name}")
                 raise
            except Exception as e:
                # Capturar cualquier otro error inesperado
                error_message = f"Error inesperado durante facturación API: {e}"
                print(f"ERROR INESPERADO API: {e}")
                _logger.exception(f"Error INESPERADO facturación API (Orden: {order.name})") # Log con traceback
                order.write({'invoice_api_response': f"Error interno: {e}"})
                # Lanzar UserError genérico
                raise UserError(_("Error interno inesperado al facturar. Contacte soporte. [%s]") % order.name)

            # Si no hubo excepciones, la facturación fue exitosa
            print(f"--- FIN Facturación API para: {order.name} (Éxito) ---")
            print("----------------------------------------")

        else:
            # La orden no requería facturación
            print(f"Orden {order.name} no requiere facturación electrónica.")

        # 4. Retornar el ID de la orden procesada. Es crucial para Odoo.
        print(f"--- FIN _process_order (Retornando ID: {order_id}) ---")
        print("----------------------------------------\n")
        return order_id


    # --- Método action_pos_order_paid (Simplificado) ---
    def action_pos_order_paid(self):
        """
        Este método ahora solo ejecuta la lógica estándar de Odoo post-pago.
        La llamada crítica a la API de facturación se movió a _process_order.
        """
        print(f"\n--- Ejecutando action_pos_order_paid para: {self.mapped('name')} ---")
        _logger.info(f"Ejecutando action_pos_order_paid para orden(es): {self.mapped('name')}")

        # Llamar al método original SUPER
        res = super(PosOrder, self).action_pos_order_paid()

        print(f"--- Fin action_pos_order_paid (para {self.mapped('name')}) ---\n")
        return res
    
    # En tu archivo models/pos_order.py
    @api.model
    def get_order_data_for_pos(self, order_id):
        order = self.browse(order_id)
        return {
            'id': order.id,
            'user_id': order.user_id.id,
            'invoice_rollo_url': order.invoice_rollo_url,
            # Otros campos que necesites
        }
    
# Añade este nuevo método a tu clase PosOrder

    def _update_invoice_with_api_data(self, api_result_data):
        """
        Actualiza la factura vinculada con datos de la API de facturación
        sin modificar otros campos contables importantes.
        
        :param api_result_data: Diccionario con los datos de la respuesta de API
        :return: Boolean indicando éxito
        """
        self.ensure_one()
        if not self.account_move:
            return False
            
        representacion_grafica = api_result_data.get('representacionGrafica', {})
        
        # Preparar solo los valores de la API para actualizar la factura
        api_update_vals = {
            'cuf': api_result_data.get('cuf'),
            'api_invoice_id': api_result_data.get('_id'),
            'pdf_url': representacion_grafica.get('pdf'),
            'sin_url': representacion_grafica.get('sin'),
            'rollo_url': representacion_grafica.get('rollo'),
            'xml_url': representacion_grafica.get('xml'),
            # Agregar otros campos importantes de la API
        }
        
        # Actualizar la factura existente
        self.account_move.sudo().write(api_update_vals)
        _logger.info(f"Factura ID: {self.account_move.id} actualizada con datos API para orden POS {self.name}")
        return True
    
    def _prepare_account_move_data(self, response_data):
        orden_pos_id = self.id  # Guardamos el ID en una variable si lo necesitas más adelante
        print(f"\n--- Preparando datos para account.move (Orden POS ID: {orden_pos_id}) ---")
        # El resto de tu lógica permanece igual...
        if not self.to_invoice:
            print(f"La orden POS {self.id} no requiere factura (to_invoice=False). No se preparan datos de account.move.")
            return {} # Devuelve un diccionario vacío si no hay nada que preparar

        """Prepara los datos completos para crear o actualizar el account.move, incluyendo líneas de productos"""
        result = response_data.get('data', {}).get('facturaCompraVentaCreate', {})
        representacion_grafica = result.get('representacionGrafica', {})
        # Asegúrate de que partner_id existe antes de intentar acceder a sus atributos
        partner = self.partner_id
        if not partner:
             print(f"ADVERTENCIA: Orden POS {self.id} sin cliente definido. Usando valores genéricos para la factura.")
             razon_social_cliente = "Sin Cliente"
             cod_tipo_doc_cliente = 5 # Por ejemplo, CI para "Sin Nombre"
             phone_cliente = ""
             email_cliente = ""
        else:
             razon_social_cliente = partner.razon_social or partner.name or 'Sin Razón Social'
             cod_tipo_doc_cliente = getattr(partner, 'codigo_tipo_documento_identidad', 5) # Usa getattr para seguridad
             phone_cliente = partner.phone
             email_cliente = partner.email

        # Método de pago (considera si puede haber más de un pago)
        codigo_metodo_pago_factura = '1' # Valor por defecto: Efectivo
        numero_tarjeta_factura = False
        if self.payment_ids:
            # Usualmente se toma el primer método de pago para la factura SIN
            primer_pago = self.payment_ids[0]
            metodo_pago_obj = primer_pago.payment_method_id
            codigo_metodo_pago_factura = getattr(metodo_pago_obj, 'metodo_pago_sin', '1')
            # Asegúrate de que sea string para la comparación
            if str(codigo_metodo_pago_factura) == '2' and self.temporary_card_number:
                 numero_tarjeta_factura = self.temporary_card_number # Usa el número temporal guardado

        # Preparar líneas de factura
        invoice_lines = []
        for line in self.lines:
            # Es buena práctica verificar si hay producto en la línea
            if not line.product_id:
                _logger.warning(f"Línea de orden POS {self.id} sin producto. Omitiendo línea en factura.")
                continue

            invoice_line_vals = {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.qty,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'product_uom_id': line.product_id.uom_id.id,
                'tax_ids': [(6, 0, line.tax_ids_after_fiscal_position.ids if hasattr(line, 'tax_ids_after_fiscal_position') and line.tax_ids_after_fiscal_position else line.tax_ids.ids)],
            }
            invoice_lines.append((0, 0, invoice_line_vals))

        # Validar si se generaron líneas de factura
        if not invoice_lines:
             _logger.error(f"No se generaron líneas de factura para la orden POS {self.id}. No se creará el asiento contable.")
             # Podrías lanzar un error o retornar diccionario vacío dependiendo de tu flujo
             # raise UserError(_("No se pudieron generar las líneas de detalle para la factura de la orden %s.") % self.name)
             return {}


        # Construcción del diccionario de valores para account.move
        move_vals = {
            'partner_id': self.partner_id.id if self.partner_id else False,
            'invoice_date': fields.Date.context_today(self),
            'move_type': 'out_invoice',
            'ref': self.name,
            'invoice_line_ids': invoice_lines,
            'invoice_origin': self.name,
            'invoice_user_id': self.user_id.id,
            'invoice_date_due': fields.Date.context_today(self),
            'currency_id': self.currency_id.id,
            'razon_social': razon_social_cliente,
            'codigo_tipo_documento_identidad': cod_tipo_doc_cliente,
            'phone': phone_cliente, # Campo estándar en Odoo es partner_id.phone
            'email': email_cliente, # Campo estándar en Odoo es partner_id.email

            # --- Datos de Pago ---
            'codigo_metodo_pago': codigo_metodo_pago_factura,
            'numero_tarjeta': numero_tarjeta_factura, # Solo si es tarjeta

            # --- Datos de la Respuesta API ---
            'cuf': result.get('cuf'),
            'api_invoice_id': result.get('_id'), # El ID de la factura en el sistema externo
            'api_invoice_state': result.get('state'), # El estado de la factura en el sistema externo
            'pdf_url': representacion_grafica.get('pdf'),
            'sin_url': representacion_grafica.get('sin'),
            'rollo_url': representacion_grafica.get('rollo'),
            'xml_url': representacion_grafica.get('xml'),
        }

        print(f"Valores preparados para account.move (Orden POS ID: {self.id}):")
        # Cuidado al imprimir diccionarios grandes en producción
        # print(json.dumps(move_vals, indent=2, default=str)) # default=str para manejar objetos no serializables

        return move_vals # Devuelve el diccionario con los valores
    
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
