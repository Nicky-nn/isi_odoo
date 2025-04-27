# -*- coding: utf-8 -*-
import random
import requests # Asegúrate de que 'requests' esté instalado en tu entorno Odoo
import json
import logging

from odoo import models, fields, api, _ # Añadir _ para traducciones/mensajes
from odoo.exceptions import UserError # Para mostrar errores al usuario si es necesario

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    # 1. Campo existente para almacenar el número de tarjeta temporalmente
    temporary_card_number = fields.Char(
        string="Número de Tarjeta Temporal",
        readonly=True,
        copy=False, # No copiar este campo al duplicar la orden
        help="Número de tarjeta ingresado en el POS para pagos con tarjeta."
    )

    # Campo para almacenar la respuesta de la API (opcional, pero útil para debugging/historial)
    invoice_api_response = fields.Text(string="Respuesta API Facturación", readonly=True, copy=False)
    invoice_pdf_url = fields.Char(string="URL PDF Factura", readonly=True, copy=False)
    invoice_xml_url = fields.Char(string="URL XML Factura", readonly=True, copy=False)
    invoice_sin_url = fields.Char(string="URL SIN Factura", readonly=True, copy=False)
    invoice_rollo_url = fields.Char(string="URL Rollo Factura", readonly=True, copy=False)

    # 2. Indicar a Odoo que lea este campo desde el JSON del POS
    @api.model
    def _order_fields(self, ui_order):
        fields_to_include = super(PosOrder, self)._order_fields(ui_order)
        # Asegúrate de que el nombre 'temporary_card_number' coincida EXACTAMENTE
        # con la clave usada en export_as_JSON en el lado del POS (main.js)
        fields_to_include['temporary_card_number'] = ui_order.get('temporary_card_number')
        return fields_to_include

    # --- Métodos para obtener configuración de la API ---

    @api.model
    def _get_api_token_for_user(self, user_id):
        """ Obtiene el token de API para un usuario específico """
        # Es mejor usar el ORM si es posible, pero mantenemos la consulta SQL
        # si el modelo isi_pass_config no está directamente relacionado
        self.env.cr.execute("""
            SELECT token FROM isi_pass_config
            WHERE user_id = %s
            LIMIT 1
        """, (user_id,))
        result = self.env.cr.fetchone()
        if not result:
            _logger.warning(f"No se encontró token de API para el usuario ID: {user_id}")
            return None
        return result[0]

    @api.model
    def _get_api_url(self, user_id):
        """ Obtiene la URL de la API para un usuario específico """
        self.env.cr.execute("""
            SELECT api_url FROM isi_pass_config
            WHERE user_id = %s
            LIMIT 1
        """, (user_id,))
        result = self.env.cr.fetchone()
        if not result:
            _logger.warning(f"No se encontró URL de API para el usuario ID: {user_id}")
            return None
        return result[0]
    
    def _get_api_config(self, user_id, column_name):
        """
        Obtiene el valor de la columna `column_name` de la tabla isi_pass_config
        para el user_id dado. Retorna None si no existe.
        """
        # (Opcional) evitar inyección validando columna
        allowed = {'sucursal_codigo', 'punto_venta_codigo'}
        if column_name not in allowed:
            raise ValueError(f"Columna no permitida: {column_name}")

        self.env.cr.execute(f"""
            SELECT {column_name} FROM isi_pass_config
            WHERE user_id = %s
            LIMIT 1
        """, (user_id,))
        row = self.env.cr.fetchone()
        if not row:
            _logger.warning(
                f"No se encontró {column_name} para el usuario ID: {user_id}"
            )
            return None
        return row[0]
# --- Método principal modificado ---

    def action_pos_order_paid(self):
        # Llamar primero al método original para que Odoo haga su procesamiento estándar
        # (crear asientos contables, marcar como pagado, etc.)
        res = super(PosOrder, self).action_pos_order_paid()

        # Iterar sobre las órdenes (aunque usualmente es una sola desde la UI)
        for order in self:
            # Imprimir información básica (como en tu código original)
            print("\n----------------------------------------")
            print(f"PROCESANDO ORDEN POS: {order.name}")
            print("----------------------------------------")
            print("CLIENTE:")
            if order.partner_id:
                print(f"  Razon Social: {order.partner_id.name}") # Usar 'name' como fallback si 'razon_social' no existe
                # Asumiendo que tienes estos campos en res.partner:
                print(f"  codigoTipoDocumentoIdentidad: {int(getattr(order.partner_id, 'codigo_tipo_documento_identidad', 'No especificado'))}")
                print(f"  codigoCliente (NIT/CI): {order.partner_id.vat or 'No especificado'}")
                print(f"  Email: {order.partner_id.email or 'No especificado'}")
                print(f"  Complemento: {getattr(order.partner_id, 'complemento', 'No especificado')}")
            else:
                print("  Cliente: Consumidor Final / No especificado")

            print("\nPRODUCTOS:")
            for i, line in enumerate(order.lines, 1):
                print(f"  {i}. {line.product_id.name}")
                print(f"     Cantidad: {line.qty}")
                print(f"     Precio unitario: {line.price_unit}")
                if line.discount:
                    descuento_monto = (line.price_unit * line.qty) * (line.discount / 100)
                    print(f"     Descuento: {descuento_monto:.2f}") # Asumiendo Bs
                print(f"     Subtotal: {line.price_subtotal}") # price_subtotal ya incluye descuento

            print("\nMÉTODOS DE PAGO:")
            if order.payment_ids:
                for payment in order.payment_ids:
                    payment_method_name = payment.payment_method_id.name
                    # Asumiendo que tienes el campo 'metodo_pago_sin' en pos.payment.method
                    metodo_pago_sin = getattr(payment.payment_method_id, 'metodo_pago_sin', 'No Definido')
                    print(f"  Método: {payment_method_name}")
                    print(f"  Método SIN: {metodo_pago_sin}")
                    # Mostrar número de tarjeta si está presente en la orden Y el método es relevante (ej: contiene 'tarjeta')
                    if order.temporary_card_number and 'tarjeta' in payment_method_name.lower():
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

            # --- Lógica de llamada a la API SI SE DEBE FACTURAR ---
            if order.to_invoice:
                print("\nINTENTANDO GENERAR FACTURA ELECTRÓNICA VÍA API...")

                # Obtener configuración de API (usando el usuario actual que procesa la orden)
                current_user_id = self.env.user.id
                token = order._get_api_token_for_user(current_user_id)
                api_url = order._get_api_url(current_user_id)

                if not token or not api_url:
                    error_message = "Error de Configuración: No se pudo obtener el Token o la URL de la API para la facturación."
                    print(f"ERROR: {error_message}")
                    order.write({'invoice_api_response': error_message}) # Guardar error
                    continue # Pasar a la siguiente orden si hubiera varias

                # --- Preparar datos para la API ---
                # Datos del cliente (con valores por defecto si no hay cliente)
                if order.partner_id:
                    cliente_data = {
                        # Usa 'name' como razon social si no existe 'razon_social'
                        "razonSocial": getattr(order.partner_id, 'razon_social', order.partner_id.name) or "Sin Nombre",
                        # Asume 'vat' es el numeroDocumento y 'codigo_tipo_documento_identidad' existe
                        "numeroDocumento": order.partner_id.vat or "0",
                        "complemento": getattr(order.partner_id, 'complemento', None), # Enviar null si no existe
                        "email": order.partner_id.email or "sin_correo@dominio.com",
                        "codigoTipoDocumentoIdentidad": int(getattr(order.partner_id, 'codigo_tipo_documento_identidad', 5)) # 5 = NIT, default si no hay
                    }
                    # Limpiar complemento si es vacío o False para que sea null en JSON
                    if not cliente_data["complemento"]:
                         cliente_data["complemento"] = None
                else:
                    # Datos por defecto para "consumidor final" según tu ejemplo
                    cliente_data = {
                        "razonSocial": "Sin Registro", # Modificado según ejemplo
                        "numeroDocumento": "0",        # Modificado según ejemplo comun para CF
                        "complemento": None,
                        "email": "sin_correo@dominio.com", # Modificado
                        "codigoTipoDocumentoIdentidad": 5 # NIT (o el código que corresponda a 'Sin Nombre'/'0')
                    }

                # Detalles de los productos
                detalle_factura = []
                for line in order.lines:
                    # Asegúrate de que estos campos existan en product.product o template
                    # Si no existen, necesitarás añadirlos o buscar alternativas
                    codigo_producto_sin = getattr(line.product_id, 'codigo_producto_sin', '83131') # Default del ejemplo
                    # Usar default_code si existe, si no, un placeholder
                    codigo_producto = line.product_id.default_code or f"PROD-{line.product_id.id}"
                    # Asumiendo que tienes un campo 'unidad_medida_sin' en product.uom
                    # o mapeas desde uom_id. Si no, usar default.
                    unidad_medida_api = getattr(line.product_id.uom_id, 'unidad_medida_sin', 1) # 1 = Unidad (default)

                    monto_descuento_linea = (line.price_unit * line.qty) * (line.discount / 100)

                    detalle_factura.append({
                        "codigoProductoSin": codigo_producto_sin,
                        "codigoProducto": codigo_producto,
                        "descripcion": line.product_id.name,
                        "cantidad": line.qty,
                        "unidadMedida": unidad_medida_api,
                        "precioUnitario": line.price_unit,
                        "montoDescuento": round(monto_descuento_linea, 2),
                        # "detalleExtra": "Opcional por línea" # Puedes añadir si lo necesitas
                    })

                # Método de pago y número de tarjeta
                # Lógica simplificada: Usa el primer método de pago encontrado.
                # Considera mejorar esto si pueden haber múltiples pagos relevantes.
                codigo_metodo_pago_api = 1 # Default: Efectivo
                numero_tarjeta_api = None
                if order.payment_ids:
                    first_payment = order.payment_ids[0]
                    # Asume que 'metodo_pago_sin' existe en pos.payment.method
                    codigo_metodo_pago_api = int(getattr(first_payment.payment_method_id, 'metodo_pago_sin', 1))

                    # Si el método de pago requiere tarjeta (ej: código 2 según tu ejemplo)
                    # Y tenemos un número de tarjeta guardado en la orden
                    if str(codigo_metodo_pago_api) == '2' and order.temporary_card_number:
                         # Limpiar y usar solo los últimos 4 dígitos o según requiera la API
                         # Aquí usamos el número completo temporalmente guardado,
                         # ¡¡ASEGÚRATE QUE ESTO CUMPLA CON PCI DSS y regulaciones locales!!
                         # Considera truncar/ofuscar si es necesario y permitido por la API.
                         # Por seguridad, solo enviaremos los últimos 4 dígitos como ejemplo:
                         # numero_tarjeta_api = order.temporary_card_number[-4:] # Ejemplo últimos 4
                         # O como pide tu ejemplo, el número completo (¡CUIDADO!)
                         numero_tarjeta_api = order.temporary_card_number # Ejemplo número completo

                    # Asegúrate de que el numeroTarjeta sea null si no aplica
                    if str(codigo_metodo_pago_api) != '2':
                        numero_tarjeta_api = None

                actividades_economicas = set()
                for line in order.lines:
                    if line.product_id.codigo_producto_homologado:
                        parts = line.product_id.codigo_producto_homologado.split(' - ')
                        if len(parts) > 0:
                            actividades_economicas.add(parts[0])

                # Si no hay actividades económicas, usar un valor por defecto
                actividad_economica = random.choice(list(actividades_economicas)) if actividades_economicas else "620000"
                # Construir el objeto 'input' para la mutación GraphQL
                # Usa valores fijos/de configuración donde sea necesario
                factura_input = {
                    "cliente": cliente_data,
                    "codigoExcepcion": 0, # 0 si no hay excepción, 1 si sí (según tu ejemplo)
                    "actividadEconomica": actividad_economica,
                    "codigoMetodoPago": codigo_metodo_pago_api,
                    "numeroTarjeta": numero_tarjeta_api, # Será null si no es pago con tarjeta o no se capturó
                    "descuentoAdicional": 0, # Ejemplo: obtener de config POS si existe
                    "codigoMoneda": 1, # 1 = Boliviano (ajusta si es necesario)
                    "tipoCambio": 1, # Ajústalo si usas otras monedas
                    # "detalleExtra": "<p><strong>Detalle global extra</strong></p>", # Opcional
                    "detalle": detalle_factura
                }

                user_id = self.env.user.id
                codigo_sucursal    = self._get_api_config(user_id, 'sucursal_codigo')    or 0
                codigo_punto_venta = self._get_api_config(user_id, 'punto_venta_codigo') or 0
                # Construir las variables completas para la query GraphQL
                graphql_variables = {
                    "entidad": {
                        "codigoSucursal":    int(codigo_sucursal),
                        "codigoPuntoVenta":  int(codigo_punto_venta),
                    },
                    "input": factura_input
                }

                # Definir la mutación GraphQL (como string)
                graphql_mutation = """
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

                # Cabeceras de la petición
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}'
                }

                # --- Realizar la llamada a la API ---
                api_success = False
                api_result_data = {}
                error_detail = "Error desconocido durante la llamada API."

                # Imprimir datos que se enviarán (¡Cuidado con datos sensibles como el token en logs de producción!)
                print("\n--- ENVIANDO DATOS A API DE FACTURACIÓN ---")
                # Clona las variables para no modificar el original al ocultar el token para el print
                variables_copy_for_print = graphql_variables.copy()
                # No imprimimos el token directamente en consola por seguridad, aunque sí lo usamos
                print(f"URL: {api_url}")
                # print(f"Headers: {headers}") # No imprimir headers completos por el token
                print("Variables (Payload):")
                print(json.dumps(variables_copy_for_print, indent=2))
                print("--- FIN DATOS A ENVIAR ---")

                try:
                    response = requests.post(
                        api_url,
                        headers=headers,
                        json={'query': graphql_mutation, 'variables': graphql_variables},
                        timeout=30 # Añadir timeout
                    )
                    response.raise_for_status() # Lanza error para códigos HTTP 4xx/5xx

                    api_response_json = response.json()

                    # Imprimir respuesta COMPLETA de la API para depuración
                    print("\n--- RESPUESTA DE LA API ---")
                    print(json.dumps(api_response_json, indent=2))
                    print("--- FIN RESPUESTA API ---")

                    # Guardar respuesta completa (texto) en la orden
                    order.write({'invoice_api_response': json.dumps(api_response_json, indent=2)})

                    # Analizar la respuesta GraphQL
                    if 'errors' in api_response_json and api_response_json['errors']:
                        # La API GraphQL devolvió errores específicos
                        error_detail = "Error en API GraphQL: " + "; ".join([e.get('message', 'Error no especificado') for e in api_response_json['errors']])
                        print(f"ERROR GraphQL: {error_detail}")

                    elif 'data' in api_response_json and api_response_json['data'].get('facturaCompraVentaCreate'):
                        # Éxito, la mutación devolvió datos
                        api_result_data = api_response_json['data']['facturaCompraVentaCreate']
                        # Verificar si la respuesta contiene lo esperado (ej: representacionGrafica)
                        if api_result_data and api_result_data.get('representacionGrafica'):
                            api_success = True
                            print("¡FACTURA GENERADA EXITOSAMENTE!")
                            # Guardar URLs y notificar
                            links = api_result_data['representacionGrafica']
                            order.write({
                                'invoice_pdf_url': links.get('pdf'),
                                'invoice_xml_url': links.get('xml'),
                                'invoice_sin_url': links.get('sin'),
                                'invoice_rollo_url': links.get('rollo'),
                            })
                            success_message = f"Factura generada exitosamente (CUF: {api_result_data.get('cuf', 'N/A')})."
                            links_html = "<ul>"
                            if links.get('pdf'): links_html += f'<li><a href="{links["pdf"]}" target="_blank">Ver PDF</a></li>'
                            if links.get('xml'): links_html += f'<li><a href="{links["xml"]}" target="_blank">Ver XML</a></li>'
                            if links.get('sin'): links_html += f'<li><a href="{links["sin"]}" target="_blank">Ver SIN</a></li>'
                            if links.get('rollo'): links_html += f'<li><a href="{links["rollo"]}" target="_blank">Ver Rollo</a></li>'
                            links_html += "</ul>"

                        else:
                            # La respuesta 'data' no tiene la estructura esperada
                            error_detail = "Respuesta exitosa de API pero formato inesperado o sin datos de factura."
                            print(f"ERROR: {error_detail}")

                    else:
                        # La respuesta JSON no tiene 'data' ni 'errors' claros
                        error_detail = "Respuesta inesperada de la API de facturación."
                        print(f"ERROR: {error_detail}")


                except requests.exceptions.Timeout:
                    error_detail = "Error de Conexión: Timeout al conectar con la API de facturación."
                    print(f"ERROR: {error_detail}")
                    order.write({'invoice_api_response': error_detail})

                except requests.exceptions.RequestException as e:
                    # Error de conexión, HTTP, etc.
                    error_detail = f"Error de Conexión/HTTP: {e}"
                    print(f"ERROR: {error_detail}")
                    # Guardar el error en la orden para referencia
                    order.write({'invoice_api_response': error_detail})
                    # Añadir mensaje en el chatter de la orden

                # --- Fin llamada API ---
                if not api_success:
                    # Aquí decidimos NO marcar la orden como no pagada, solo mostramos/registramos el error.
                    # La orden ya fue marcada como pagada por el super() al inicio.
                    print(f"La generación de la factura falló, pero la orden {order.name} se mantiene pagada en Odoo.")
                    # Podrías añadir lógica adicional aquí si fuera necesario, como crear una actividad
                    # para revisar manualmente la facturación fallida.
                    # self.env['mail.activity'].create({
                    #     'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    #     'res_id': order.id,
                    #     'res_model_id': self.env.ref('point_of_sale.model_pos_order').id,
                    #     'user_id': self.env.user.id, # O un usuario específico de facturación
                    #     'summary': 'Revisar fallo API Facturación',
                    #     'note': f'La llamada API para la orden {order.name} falló. Error: {error_detail}',
                    # })

            else:
                print("\nEsta orden no requiere facturación electrónica.")

            print(f"\n--- FIN PROCESAMIENTO ORDEN {order.name} ---")


        # Devolver el resultado del método original
        return res

# Nota importante sobre Seguridad y Sensibilidad de Datos:
# - El campo `temporary_card_number` almacena información sensible. Asegúrate de cumplir
#   con PCI DSS y las normativas locales sobre almacenamiento y transmisión de números de tarjeta.
#   Lo ideal es no almacenar el número completo o hacerlo solo el tiempo estrictamente necesario
#   y con medidas de seguridad adecuadas (encriptación, logs de acceso, etc.).
# - El código actual envía el número de tarjeta completo (si está disponible) a la API.
#   Verifica si esto es requerido y permitido. A menudo, solo se envían los últimos 4 dígitos
#   o un token de pago en lugar del número real. ¡Adapta esto según tus requisitos y seguridad!
# - Evita imprimir información sensible como tokens de API o números de tarjeta completos
#   en logs de producción. Usa `_logger.debug` o elimina esos prints antes de desplegar.

# Notas sobre campos asumidos (DEBES VERIFICAR/CREARLOS):
# - En `res.partner`: `razon_social`, `codigo_tipo_documento_identidad`, `complemento`.
# - En `product.product` o `product.template`: `codigo_producto_sin`.
# - En `product.uom`: `unidad_medida_sin` (o alguna forma de mapear la unidad de medida de Odoo a la requerida por la API).
# - En `pos.payment.method`: `metodo_pago_sin`.
# - En `pos.config`: `codigo_sucursal_sin`, `codigo_punto_venta_sin`, `descuento_adicional` (si aplica).
# - En `res.company`: `codigo_actividad_economica`.
# - El modelo `isi_pass_config` con campos `user_id`, `token`, `api_url`.