from odoo import models, fields, api

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        
        # Añadir campos adicionales al search_params
        result['search_params']['fields'].extend([
            'sequence',
            'outstanding_account_id',
            'receivable_account_id',
            'journal_id',
            'company_id',
            'create_uid',
            'write_uid',
            'use_payment_terminal',
            'name',
            'is_cash_count',
            'split_transactions',
            'active',
            'create_date',
            'write_date',
            'is_online_payment',
            'metodo_pago_sin',
            'facturacion_obligatoria',
        ])
        
        return result

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    # Definir los campos nuevos si no existen
    # metodo_pago_sin = fields.Integer(string='Método de Pago Sin', readonly=False)
    # facturacion_obligatoria = fields.Boolean(string='Facturación Obligatoria', default=False)

    def _get_payment_method_information(self):
        result = super()._get_payment_method_information()
        
        # Asegurar que los campos personalizados se incluyan en la información del método de pago
        for payment_method in self:
            result[payment_method.id].update({
                'metodo_pago_sin': payment_method.metodo_pago_sin,
                'facturacion_obligatoria': payment_method.facturacion_obligatoria,
                'sequence': payment_method.sequence,
                'outstanding_account_id': payment_method.outstanding_account_id.id if payment_method.outstanding_account_id else False,
                'receivable_account_id': payment_method.receivable_account_id.id if payment_method.receivable_account_id else False,
                'journal_id': payment_method.journal_id.id if payment_method.journal_id else False,
            })
        
        return result