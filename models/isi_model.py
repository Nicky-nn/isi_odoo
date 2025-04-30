from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_order(self):
        res = super()._loader_params_pos_order()
        # Añadimos invoice_pdf_url a los campos que el POS cargará
        res['search_params']['fields'].append('invoice_pdf_url')
        return res
