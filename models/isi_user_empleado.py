from odoo import fields, models

class HrEmployee(models.Model):
    # State: Completado 

    # Clase que representa un empleado en el sistema.
    # - Atributos:
    #   - isi_pass_config_ids: Relación uno a muchos con las configuraciones ISI


    _inherit = 'hr.employee'

    isi_pass_config_ids = fields.One2many('isi.pass.config', 'employee_id', string='Configuraciones ISI-PASS')