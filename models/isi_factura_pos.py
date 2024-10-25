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

    def action_pos_order_paid(self):
        print("\n----------------------------------------")
        print("Iniciando proceso de facturación")
        print("----------------------------------------")

        # Estructura del cliente
        cliente = {}
        if self.partner_id:
            cliente = {
                'razonSocial': self.partner_id.razon_social or 'Sin Razón Social',
                'numeroDocumento': self.partner_id.vat or '',
                'email': self.partner_id.email or '',
                'codigoTipoDocumentoIdentidad': self.partner_id.codigo_tipo_documento_identidad or 1,
                'complemento': self.partner_id.complemento or ''
            }
        else:
            cliente = {
                'razonSocial': 'Sin Razón Social',
                'numeroDocumento': '',
                'email': '',
                'codigoTipoDocumentoIdentidad': 1
            }

        # Estructura del detalle
        detalle = []
        codigos_producto_sin = []

        for line in self.lines:
            # Obtener los productos q son combos
            print(f"Producto: {line.product_id.name}")
            try:
                item_detalle = {
                    'codigoProductoSin': line.product_id.codigo_producto_homologado.split(' - ')[1] or '',
                    'codigoProducto': line.product_id.default_code or '',
                    'descripcion': line.product_id.name,
                    'cantidad': line.qty,
                    'unidadMedida': int(line.product_id.codigo_unidad_medida.split(' - ')[0]) or '',
                    'precioUnitario': line.price_unit,
                    'montoDescuento': line.price_unit * line.qty * line.discount / 100,
                    'detalleExtra': '',
                }
                detalle.append(item_detalle)

            except Exception as e:
                print(f"Error procesando producto {
                      line.product_id.name}: {str(e)}")
                _logger.error(f"Error procesando producto: {str(e)}")

        actividad_economica = random.choice(
            codigos_producto_sin) if codigos_producto_sin else '620000'

        # Determinar el metodo de pago y numero de tarjeta
        numero_tarjeta = None
        codigo_metodo_pago = 1  # Valor por defecto

        if self.payment_ids:
            payment = self.payment_ids[0]
            try:
                codigo_metodo_pago = int(
                    payment.payment_method_id.metodo_pago_sin)
            except:
                print(
                    "ADVERTENCIA: No se pudo obtener método de pago SIN, usando valor por defecto")

            if codigo_metodo_pago == 2:
                numero_tarjeta = "00000000"

        # Estructura de la factura completa
        factura = {
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

        print("\n----------------------------------------")
        print("Factura completa:")
        print(json.dumps(factura, indent=2))
        print("----------------------------------------")

        # Marcar como pagado
        self.write({'state': 'paid'})

        print("\nOrden marcada como pagada")
        print("----------------------------------------\n")

        return True
