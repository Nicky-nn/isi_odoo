
from odoo import models, fields, api, http
from odoo.http import request
import requests
import base64
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    rollo_pdf = fields.Binary("PDF del Rollo", attachment=True)

    def action_pos_order_paid(self):
        print("________________________________________")
        print("Iniciando proceso de facturación")
        print("________________________________________")

        # Logging información del cliente
        if self.partner_id:
            print("________________________________________")
            print("Datos del Cliente:")
            print(f"Nombre: {self.partner_id.name}")
            print(f"RAZON SOCIAL: {self.partner_id.razon_social}")
            print(f"Complemento: {self.partner_id.complemento or ''}")
            print(f"CODIGO TIPO DOCUMENTO: {self.partner_id.codigo_tipo_documento_identidad}")
            print(f"E-Mail: {self.partner_id.email}")
            print(f"ID Cliente: {self.partner_id.id}")
            print(f"VAT/NIF: {self.partner_id.vat or ''}")
            print(f"Celular: {self.partner_id.mobile or ''}")
        else:
            print("Cliente: No especificado")

        # Logging productos
        print("________________________________________")
        print("Productos en la orden:")
        for line in self.lines:
            print(f"- Producto: {line.product_id.name}")
            print(f"  Código Producto: {line.product_id.default_code}")
            print(f"  Código Producto SIN: {line.product_id.codigo_producto_homologado}")
            print(f"  Código Unidad de Medida: {line.product_id.codigo_unidad_medida}")
            print(f"  Cantidad: {line.qty}")
            print(f"  Precio unitario: {line.price_unit}")
            # Convertimos el descuento de porcentaje a monetario
            print(f"  Monto Descuento: {line.price_unit * line.qty * line.discount / 100}")
            print(f"  Subtotal: {line.price_subtotal}")

        # Logging métodos de pago
        print("________________________________________")
        print("Métodos de pago:")
        for payment in self.payment_ids:
            print(f"- Método: {payment.payment_method_id.name}")
            print(f"  Codigo Metodo: {payment.payment_method_id.metodo_pago_sin}")
        # Logging totales
        print("________________________________________")
        print(f"Subtotal: {self.amount_total - self.amount_tax}")
        print(f"IVA: {self.amount_tax}")
        print(f"Total: {self.amount_total}")
        print("________________________________________")

        # Marcar como pagado
        self.write({'state': 'paid'})

        return True