import base64
import re
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import requests
import logging
import json
import random
from odoo import _

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):

    #State: Completed

    # Esta clase extiende el modelo 'account.move' para agregar campos y 
    # funcionalidades adicionales relacionados con la facturación y 
    # la integración con una API externa para la gestión de facturas.

    # Attributes:
    #     extra_details (Html): Detalles adicionales de la factura en formato HTML.
    #     additional_discount (Float): Descuento adicional aplicado a la factura.
    #     gift_card_amount (Float): Monto aplicado de una tarjeta de regalo.
    #     custom_subtotal (Float): Subtotal calculado de la factura.
    #     custom_total (Float): Total calculado de la factura después de aplicar descuentos.
    #     codigo_metodo_pago (Selection): Método de pago seleccionado.
    #     punto_venta_codigo (Char): Código del punto de venta.
    #     punto_venta_nombre (Char): Nombre del punto de venta.
    #     punto_venta_descripcion (Char): Descripción del punto de venta.
    #     sucursal_codigo (Char): Código de la sucursal.
    #     sucursal_direccion (Char): Dirección de la sucursal.
    #     razon_social (Char): Razón social del cliente, relacionada con el socio (partner).
    #     phone (Char): Teléfono del cliente, relacionado con el socio (partner).
    #     email (Char): Correo electrónico del cliente, relacionado con el socio (partner).
    #     codigo_tipo_documento_identidad (Selection): Tipo de documento de identidad del cliente.
    #     cuf (Char): Código único de factura.
    #     api_invoice_id (Char): Identificador de factura en la API.
    #     api_invoice_state (Char): Estado de la factura en la API.
    #     pdf_url (Char): URL para descargar el PDF de la factura.
    #     sin_url (Char): URL para la representación gráfica en el SIN.
    #     rollo_url (Char): URL para el rollo de la factura.
    #     xml_url (Char): URL para el archivo XML de la factura.
    #     numero_tarjeta (Char): Número de tarjeta para el pago (primeros 4 y últimos 4 dígitos).
    #     permitir_nit_invalido (Boolean): Indica si se permite la facturación con NIT inválido.

    # Methods:
    #     get_token_for_user(): Obtiene el token de autenticación para el usuario actual.
    #     get_api_url(): Obtiene la URL de la API para la integración.
    #     get_payment_methods_from_api(): Obtiene los métodos de pago desde la API.
    #     _get_payment_method_selection(): Devuelve la selección de métodos de pago.
    #     _get_default_payment_method(): Devuelve el método de pago predeterminado.
    #     _onchange_codigo_metodo_pago(): Actualiza el campo de número de tarjeta según el método de pago seleccionado.
    #     _prepare_card_number(numero_tarjeta): Prepara el número de tarjeta para el envío a la API.
    #     _compute_custom_subtotal(): Calcula el subtotal personalizado de la factura.
    #     _compute_custom_total(): Calcula el total personalizado de la factura.
    #     action_post(): Publica la factura y envía a la API si es una factura de venta.
    #     actualizar_estado_factura(): Actualiza el estado de la factura consultando la API.
    #     create(vals): Crea un nuevo registro de factura y actualiza el estado si ya tiene un CUF.
    #     write(vals): Actualiza un registro de factura y actualiza el estado si se ha cambiado el CUF.
    #     button_draft(): Revierte el estado de la factura a borrador y limpia los campos relacionados con la API.
    #     enviar_factura_a_api(): Envía la factura a la API para su procesamiento.
    #     _log_api_error(error_message): Registra un error relacionado con la API y notifica al usuario.
    #     get_invoice_details(): Obtiene los detalles de la factura para enviar a la API.
    #     _onchange_partner_id(): Actualiza los campos relacionados con el socio (partner) al cambiar el cliente.
    #     default_get(fields_list): Obtiene los valores predeterminados para los campos de la factura.
    #     _get_default_punto_venta_sucursal(): Obtiene los valores predeterminados para los campos de punto de venta y sucursal.
    #     action_send_and_print(): Envía la factura a la API y muestra el PDF de la factura.
    #     action_print_rollo(): Descarga el PDF del rollo de la factura.
    #     action_send_whatsapp(): Envía la factura por WhatsApp al cliente.

    _inherit = 'account.move'

    # Campos existentes
    extra_details = fields.Html(string="Detalles Extra")
    additional_discount = fields.Float(string="Descuento Adicional", default=0.0)
    gift_card_amount = fields.Float(string="Monto Gift Card", default=0.0)
    custom_subtotal = fields.Float(string="Sub-Total", compute='_compute_custom_subtotal', store=True)
    custom_total = fields.Float(string="Total", compute='_compute_custom_total', store=True)
    codigo_metodo_pago = fields.Selection(
        selection='_get_payment_method_selection',
        string='Método de Pago',
        default=lambda self: self._get_default_payment_method()
    )
    punto_venta_codigo = fields.Char(string="Código Punto de Venta")
    punto_venta_nombre = fields.Char(string="Nombre Punto de Venta")
    punto_venta_descripcion = fields.Char(string="Descripción Punto de Venta")
    sucursal_codigo = fields.Char(string="Código Sucursal")
    sucursal_direccion = fields.Char(string="Dirección Sucursal")
    razon_social = fields.Char(string="Razón Social", related='partner_id.razon_social', readonly=False)
    phone = fields.Char(string="Teléfono", related='partner_id.phone', readonly=False)
    email = fields.Char(string="Correo Electrónico", related='partner_id.email', readonly=False)
    codigo_tipo_documento_identidad = fields.Selection(
        selection=lambda self: self.env['res.partner']._get_document_type_selection(),
        string='Documento de Identidad',
        related='partner_id.codigo_tipo_documento_identidad',
        readonly=False
    )

    # Campos para almacenar la respuesta de la API
    cuf = fields.Char(string="CUF", readonly=True)
    api_invoice_id = fields.Char(string="ID de Factura API", readonly=True)
    api_invoice_state = fields.Char(string="Estado de Factura API", readonly=True)
    pdf_url = fields.Char(string="URL del PDF", readonly=True)
    sin_url = fields.Char(string="URL del SIN", readonly=True)
    rollo_url = fields.Char(string="URL del Rollo", readonly=True)
    xml_url = fields.Char(string="URL del XML", readonly=True)

    # Nuevo campo para número de tarjeta
    numero_tarjeta = fields.Char(string="Número de Tarjeta", help="Primeros 4 y últimos 4 dígitos de la tarjeta")

    # Nuevo campo para permitir facturación con NIT inválido
    permitir_nit_invalido = fields.Boolean(string="Permitir facturación con NIT inválido", default=False)

    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.discount')
    def _compute_custom_subtotal(self):
        for move in self:
            move.custom_subtotal = sum(line.price_subtotal for line in move.invoice_line_ids)

    @api.depends('custom_subtotal', 'additional_discount', 'gift_card_amount')
    def _compute_custom_total(self):
        for move in self:
            move.custom_total = move.custom_subtotal - move.additional_discount - move.gift_card_amount

    @api.model
    def get_token_for_user(self):
        current_user_id = self.env.user.id
        self.env.cr.execute("""
            SELECT token FROM isi_pass_config
            WHERE user_id = %s
            LIMIT 1
        """, (current_user_id,))
        result = self.env.cr.fetchone()
        return result[0] if result else None

    @api.model
    def get_api_url(self):
        self.env.cr.execute("""
            SELECT api_url FROM isi_pass_config
            WHERE user_id = %s
            LIMIT 1
        """, (self.env.user.id,))
        result = self.env.cr.fetchone()
        return result[0] if result else None

    @api.model
    def get_payment_methods_from_api(self):
        token = self.get_token_for_user()
        api_url = self.get_api_url()

        if not token or not api_url:
            _logger.error("No se pudo obtener el token o la URL de la API")
            return []

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        query = """
        query METODOS_PAGO {
            metodosPago {
                codigoClasificador
                descripcion
            }
        }
        """

        try:
            response = requests.post(api_url, json={'query': query}, headers=headers)
            response.raise_for_status()
            data = response.json()
            methods = [(str(method['codigoClasificador']), method['descripcion']) for method in data['data']['metodosPago']]
            if methods:
                methods[0] = (methods[0][0], f"{methods[0][1]} (Predeterminado)")
            return methods
        except requests.RequestException as e:
            _logger.error(f"Error al obtener métodos de pago de la API: {str(e)}")
            return []

    @api.model
    def _get_payment_method_selection(self):
        methods = self.get_payment_methods_from_api()
        if not methods:
            _logger.warning("No se pudieron obtener métodos de pago de la API. El campo de selección estará vacío.")
        return methods

    @api.model
    def _get_default_payment_method(self):
        methods = self.get_payment_methods_from_api()
        return methods[0][0] if methods else False

    @api.onchange('codigo_metodo_pago')
    def _onchange_codigo_metodo_pago(self):
        if self.codigo_metodo_pago == '2':  # Asumiendo que '2' es el código para tarjeta
            self.numero_tarjeta = ''
        else:
            self.numero_tarjeta = False

    def _prepare_card_number(self, numero_tarjeta):
        if numero_tarjeta and len(numero_tarjeta) == 8:
            return f"{numero_tarjeta[:4]}{'0' * 8}{numero_tarjeta[-4:]}"
        return None
    

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self.filtered(lambda m: m.move_type == 'out_invoice' and m.state == 'posted'):
            try:
                move.with_context(show_loading=True).enviar_factura_a_api()
                
                # Obtener 'metodo_pago_sin' desde el diario asociado a la factura
                metodo_pago_sin = move.journal_id.metodo_pago_sin  # Accedemos al campo en 'account.journal'
                if metodo_pago_sin:
                    # Buscar un diario que coincida con 'metodo_pago_sin'
                    journal = self.env['account.journal'].search([('metodo_pago_sin', '=', metodo_pago_sin)], limit=1)
                    if journal:
                        # Obtener el método de pago desde 'inbound_payment_method_line_ids'
                        payment_method_line = journal.inbound_payment_method_line_ids[:1]
                        payment_method_id = payment_method_line.payment_method_id.id if payment_method_line else False

                        # Crear el pago y asociarlo a la factura
                        payment_vals = {
                            'payment_type': 'inbound',
                            'partner_type': 'customer',
                            'partner_id': move.partner_id.id,
                            'amount': move.amount_residual,
                            'journal_id': journal.id,
                            'payment_method_id': payment_method_id,
                            'payment_date': fields.Date.today(),
                            'communication': move.name,
                            'invoice_ids': [(6, 0, [move.id])],  # Asociar el pago a la factura
                        }
                        payment = self.env['account.payment'].create(payment_vals)
                        payment.action_post()
                    else:
                        _logger.info(f"No se encontró un diario con 'metodo_pago_sin' '{metodo_pago_sin}'. No se registrará el pago automáticamente.")
                else:
                    _logger.info("El diario asociado a la factura no tiene definido 'metodo_pago_sin'. No se registrará el pago automáticamente.")

            except ValidationError as e:
                self.env.user.notify_warning(message=str(e), title="Error al enviar factura a API", sticky=True)
        return res

    def actualizar_estado_factura(self):
        self.ensure_one()
        if not self.cuf:
            return False

        token = self.get_token_for_user()
        api_url = self.get_api_url()

        if not token or not api_url:
            _logger.error("No se pudo obtener el token o la URL de la API")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        query = """
        query LISTADO2 {
            facturaCompraVentaAll(
                limit: 1
                page: 1
                reverse: true
                query: "cuf=%s"
            ) {
                docs {
                    state
                    representacionGrafica {
                        pdf
                        sin
                        rollo
                        xml
                    }
                }
            }
        }
        """ % self.cuf

        try:
            response = requests.post(api_url, json={'query': query}, headers=headers)
            response.raise_for_status()
            data = response.json()

            if 'errors' in data:
                _logger.error(f"Error al obtener datos de la API: {json.dumps(data['errors'], indent=2)}")
                return False

            factura_data = data['data']['facturaCompraVentaAll']['docs'][0]
            self.api_invoice_state = factura_data['state']
            
            rep_grafica = factura_data['representacionGrafica']
            self.pdf_url = rep_grafica['pdf']
            self.sin_url = rep_grafica['sin']
            self.rollo_url = rep_grafica['rollo']
            self.xml_url = rep_grafica['xml']

            _logger.info(f"Estado de la factura {self.name} actualizado correctamente.")
            return True
        except Exception as e:
            _logger.error(f"Error al actualizar el estado de la factura {self.name}: {str(e)}")
            return False

    @api.model
    def create(self, vals):
        record = super(AccountMove, self).create(vals)
        if record.cuf:
            record.actualizar_estado_factura()
        return record

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        if 'cuf' in vals and vals['cuf']:
            for record in self:
                record.actualizar_estado_factura()
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        for move in self:
            move.cuf = False
            move.api_invoice_id = False
            move.api_invoice_state = False
        return res

    def enviar_factura_a_api(self):
        self.ensure_one()
        if self.api_invoice_id:
            _logger.info(f"La factura {self.name} ya ha sido enviada a la API.")
            return False

        token = self.get_token_for_user()
        api_url = self.get_api_url()

        if not token or not api_url:
            self._log_api_error("No se pudo obtener el token o la URL de la API")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        mutation = """
        mutation FCV_REGISTRO_ONLINE($input: FacturaCompraVentaInput!) {
            facturaCompraVentaCreate(
                entidad: { codigoSucursal: %s, codigoPuntoVenta: %s }
                input: $input
            ) {
                _id
                cuf
                cliente {
                    _id
                    razonSocial
                }
                state
            }
        }
        """ % (self.sucursal_codigo, self.punto_venta_codigo)

        # Obtener actividades económicas únicas de las líneas de factura
        actividades_economicas = set()
        for line in self.invoice_line_ids:
            if line.product_id.codigo_producto_homologado:
                parts = line.product_id.codigo_producto_homologado.split(' - ')
                if len(parts) > 0:
                    actividades_economicas.add(parts[0])

        # Si no hay actividades económicas, usar un valor por defecto
        actividad_economica = random.choice(list(actividades_economicas)) if actividades_economicas else "620000"

        # Preparar el número de tarjeta si es necesario
        numero_tarjeta = self._prepare_card_number(self.numero_tarjeta) if self.codigo_metodo_pago == '2' else None

        variables = {
            "input": {
                "cliente": {
                    # Razon o nombre del cliente
                    "razonSocial": self.razon_social or self.partner_id.name,
                    "numeroDocumento": self.partner_id.vat,
                    "email": self.email,
                    "codigoTipoDocumentoIdentidad": int(self.codigo_tipo_documento_identidad),
                },
                "codigoExcepcion": 1 if self.permitir_nit_invalido else 0,
                "actividadEconomica": actividad_economica,
                "codigoMetodoPago": int(self.codigo_metodo_pago),
                "numeroTarjeta": numero_tarjeta,
                "descuentoAdicional": self.additional_discount,
                "codigoMoneda": 1,
                "tipoCambio": 1,
                "detalleExtra": self.extra_details or "",
                "detalle": self.get_invoice_details()
            }
        }

        try:
            _logger.info(f"Enviando factura {self.name} a la API. Datos: {json.dumps(variables, indent=2)}")
            
            if self.env.context.get('show_loading'):
                self.env.cr.execute("SELECT pg_advisory_lock(1)")
            
            response = requests.post(api_url, json={'query': mutation, 'variables': variables}, headers=headers)
            
            _logger.info(f"Respuesta de la API para factura {self.name}. Status: {response.status_code}, Contenido: {response.text}")
            
            response.raise_for_status()
            data = response.json()

            if 'errors' in data:
                error_message = json.dumps(data['errors'], indent=2)
                self._log_api_error(f"Error al enviar la factura a la API: {error_message}")
                return False

            # Procesar la respuesta exitosa
            invoice_data = data['data']['facturaCompraVentaCreate']
            self.write({
                'cuf': invoice_data['cuf'],
                'api_invoice_id': invoice_data['_id'],
                'api_invoice_state': invoice_data['state'],
            })

            self.message_post(body="Factura enviada exitosamente a la API.")
            _logger.info(f"Factura {self.name} enviada exitosamente a la API.")

            # Notify success (you might need to adapt this based on your Odoo version and setup)
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'notification', {
                'type': 'success',
                'message': _("PDF del rollo descargado correctamente."),
            })
        

            return True
        except requests.RequestException as e:
            error_msg = f"Error al enviar la factura {self.name} a la API: {str(e)}"
            if hasattr(e.response, 'text'):
                error_msg += f"\nDetalles del error: {e.response.text}"
            self._log_api_error(error_msg)
            return False
        except Exception as e:
            self._log_api_error(f"Error inesperado al enviar la factura {self.name} a la API: {str(e)}")
            return False
        finally:
            if self.env.context.get('show_loading'):
                self.env.cr.execute("SELECT pg_advisory_unlock(1)")

    def _log_api_error(self, error_message):
        self.message_post(body=error_message, message_type='comment')
        _logger.error(error_message)
        return error_message  # Devolver el mensaje de error en lugar de lanzar una excepción


    def get_invoice_details(self):
        details = []
        for line in self.invoice_line_ids:
            # Skip products with price unit of 0
            if line.price_unit == 0:
                continue

            codigo_producto_homologado = line.product_id.codigo_producto_homologado or ""
            parts = codigo_producto_homologado.split(' - ')
            codigo_producto_sin = parts[1] if len(parts) > 1 else "99100"

            detail = {
                "codigoProductoSin": codigo_producto_sin,
                "codigoProducto": line.product_id.default_code or "",
                "descripcion": line.name,
                "cantidad": line.quantity,
                "unidadMedida": int(re.match(r'\d+', line.product_id.codigo_unidad_medida).group()) if line.product_id.codigo_unidad_medida and re.match(r'\d+', line.product_id.codigo_unidad_medida) else 1,
                "precioUnitario": line.price_unit,
                "montoDescuento": line.discount,
                "detalleExtra": ""
            }
            details.append(detail)
        return details

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.razon_social = self.partner_id.razon_social
            self.phone = self.partner_id.phone
            self.email = self.partner_id.email
            self.codigo_tipo_documento_identidad = self.partner_id.codigo_tipo_documento_identidad
        else:
            self.razon_social = False
            self.phone = False
            self.email = False
            self.codigo_tipo_documento_identidad = False

    @api.model
    def default_get(self, fields_list):
        defaults = super(AccountMove, self).default_get(fields_list)
        defaults.update(self._get_default_punto_venta_sucursal())
        return defaults

    @api.model
    def _get_default_punto_venta_sucursal(self):
        current_user_id = self.env.user.id
        self.env.cr.execute("""
            SELECT punto_venta_codigo, punto_venta_nombre, punto_venta_descripcion,
                   sucursal_codigo, sucursal_direccion
            FROM isi_pass_config
            WHERE user_id = %s
            LIMIT 1
        """, (current_user_id,))
        result = self.env.cr.fetchone()
        if result:
            return {
                'punto_venta_codigo': result[0],
                'punto_venta_nombre': result[1],
                'punto_venta_descripcion': result[2],
                'sucursal_codigo': result[3],
                'sucursal_direccion': result[4],
            }
    
    def extraer_numero(codigo):
        # Buscar el primer número en la cadena
        match = re.match(r'\d+', codigo)
        # Si se encuentra un número, convertirlo a int, de lo contrario retornar 1
        return int(match.group()) if match else 1

    def action_send_and_print(self):
        self.ensure_one()
        if not self.cuf:
            self.enviar_factura_a_api()

        pdf_type = self.env.context.get('pdf_type', 'pdf')
        download = self.env.context.get('download', False)
        email = self.env.context.get('email', False)
        whatsapp = self.env.context.get('whatsapp', False)

        # Obtener la URL del PDF correspondiente
        if pdf_type == 'pdf':
            pdf_url = self.pdf_url
        else:
            pdf_url = self.rollo_url

        if not pdf_url:
            self._log_api_error(f"No se pudo obtener la URL del PDF de tipo {pdf_type.upper()}")

        # Descargar el PDF
        try:
            response = requests.get(pdf_url)
            response.raise_for_status()
            pdf_content = response.content
        except requests.RequestException as e:
            self._log_api_error(f"Error al descargar el PDF de la factura: {str(e)}")

        # Crear un adjunto con el PDF
        attachment = self.env['ir.attachment'].create({
            'name': f"Factura_{self.name}_{pdf_type}.pdf",
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
        })

        actions = []

        if download:
            actions.append({
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            })

        return actions if actions else {'type': 'ir.actions.act_window_close'}


    
    def action_print_rollo(self):
        self.ensure_one()
        if not self.cuf:
            self.enviar_factura_a_api()

        pdf_type = self.env.context.get('pdf_type', 'pdf')
        download = self.env.context.get('download', False)

        # Obtener la URL del PDF correspondiente
        if pdf_type == 'rollo':
            pdf_url = self.rollo_url
        else:
            pdf_url = self.rollo_url

        if not pdf_url:
            self._log_api_error(f"No se pudo obtener la URL del PDF de tipo {pdf_type.upper()}")

        # Descargar el PDF
        try:
            response = requests.get(pdf_url)
            response.raise_for_status()
            pdf_content = response.content
        except requests.RequestException as e:
            self._log_api_error(f"Error al descargar el PDF de la factura: {str(e)}")

        # Crear un adjunto con el PDF
        attachment = self.env['ir.attachment'].create({
            'name': f"Factura_{self.name}_{pdf_type}.pdf",
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
        })

        actions = []

        if download:
            actions.append({
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            })

        return actions if actions else {'type': 'ir.actions.act_window_close'}

    def action_send_whatsapp(self):
        api_url = self.get_api_url()
        token = self.get_token_for_user()

        razon_social = self.partner_id.razon_social or ''
        nit = self.partner_id.vat or ''
        urlPDF = self.pdf_url.replace('"', '\\"')
        telefono = self.phone or ''

        print('__________________________')
        print('__________________________')
        print('RAZON SOCIAL: ', razon_social)
        print('NIT: ', nit)
        print('URL PDF: ', urlPDF)
        print('TELEFONO: ', telefono)
        print('__________________________')
        print('__________________________')


        mensaje = f"""Estimado Sr(a) {razon_social},

Se ha generado el presente documento fiscal de acuerdo al siguiente detalle:

FACTURA COMPRA/VENTA

Razón Social: {razon_social}
NIT/CI/CEX: {nit}

Si recibiste este mensaje por error o tienes alguna consulta acerca de su contenido, comunícate con el remitente.

Agradecemos tu preferencia.""".replace('"', '\\"').replace('\n', '\\n')

        mutation = f"""
        mutation ENVIAR_ARCHIVO {{
            waapiEnviarUrl(
                entidad: {{ codigoSucursal: 0, codigoPuntoVenta: 0 }},
                input: {{
                    nombre: "Factura",
                    mensaje: "{mensaje}",
                    url: "{urlPDF}",
                    codigoArea: "591",
                    telefono: "{telefono}"
                }}
            ) {{
                waapiStatus
            }}
        }}
        """

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        response = requests.post(api_url, json={'query': mutation}, headers=headers)
        response_data = response.json()

        if 'errors' in response_data:
            error_message = response_data['errors'][0]['message']
            raise UserError(f"Error al enviar el mensaje: {error_message}")
        else:
            print('RESPONSE: ', response.text)

        if response.status_code == 200:
            print('Mensaje enviado correctamente')
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'success',
                'title': 'Mensaje enviado',
                'message': 'Mensaje enviado correctamente',
                'sticky': False
            })
        else:
            raise UserError(f"Error al enviar el mensaje: {response.text}")


    def preview_invoice(self):
        self.ensure_one()
        if not self.pdf_url:
            self._log_api_error("No se pudo obtener la URL del PDF de la factura")
        
        return {
            'type': 'ir.actions.act_url',
            'url': self.pdf_url,
            'target': 'self',
        }