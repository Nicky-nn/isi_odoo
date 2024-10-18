# from odoo import api, fields, models
# import requests
# import json
# import hashlib

# from odoo.exceptions import UserError


# class ISIPassConfig(models.Model):
#     _name = 'isi.pass.config'
#     _description = 'Configuración de ISI-PASS'

#     name = fields.Char(
#         'Nombre', default='Configuración ISI-PASS', required=True)
#     environment = fields.Selection([
#         ('sandbox', 'Sandbox'),
#         ('production', 'Producción')
#     ], string='Entorno', required=True, default='sandbox')
#     api_url = fields.Char(
#         'URL de API', compute='_compute_api_url', readonly=True)
#     shop_url = fields.Char('URL de Comercio', required=True)
#     email = fields.Char('Correo Electrónico', required=True)
#     password = fields.Char('Contraseña', required=True)
#     token = fields.Char('Token', readonly=True)
#     token_display = fields.Char(
#         'Token Display', compute='_compute_token_display')
#     refresh_token = fields.Char('Refresh Token', readonly=True)
#     refresh_token_display = fields.Char(
#         'Refresh Token Display', compute='_compute_refresh_token_display')
#     nombres = fields.Char('Nombres', readonly=True)
#     apellidos = fields.Char('Apellidos', readonly=True)
#     avatar = fields.Char('Avatar URL', compute='_compute_avatar', store=True)
#     razon_social = fields.Char('Razón Social', readonly=True)
#     codigo_modalidad = fields.Char('Código Modalidad', readonly=True)
#     codigo_ambiente = fields.Char('Código Ambiente', readonly=True)
#     fecha_validez_token = fields.Char('Fecha Validez Token', readonly=True)
#     tienda = fields.Char('Tienda', readonly=True)
#     email_empresa = fields.Char('Email Empresa', readonly=True)
#     email_fake = fields.Char('Email Fake', readonly=True)
#     sucursal_codigo = fields.Char('Código Sucursal', readonly=True)
#     sucursal_direccion = fields.Char('Dirección Sucursal', readonly=True)
#     sucursal_telefono = fields.Char('Teléfono Sucursal', readonly=True)
#     departamento_codigo = fields.Char('Código Departamento', readonly=True)
#     departamento_codigo_pais = fields.Char('Código País', readonly=True)
#     departamento_sigla = fields.Char('Sigla Departamento', readonly=True)
#     departamento_nombre = fields.Char('Nombre Departamento', readonly=True)

#     @api.depends('environment')
#     def _compute_api_url(self):
#         for record in self:
#             if record.environment == 'sandbox':
#                 record.api_url = 'https://sandbox.isipass.net/api'
#             else:
#                 record.api_url = 'https://api.isipass.com.bo/api'

#     @api.depends('email')
#     def _compute_avatar(self):
#         for record in self:
#             if record.email:
#                 hash = hashlib.md5(record.email.lower().encode()).hexdigest()
#                 record.avatar = f"https://www.gravatar.com/avatar/{hash}?d=mp&s=200"
#             else:
#                 record.avatar = "https://www.gravatar.com/avatar/?d=monsterid"

#     @api.depends('token')
#     def _compute_token_display(self):
#         for record in self:
#             if record.token:
#                 record.token_display = record.token[:10] + '...'
#             else:
#                 record.token_display = ''

#     @api.depends('refresh_token')
#     def _compute_refresh_token_display(self):
#         for record in self:
#             if record.refresh_token:
#                 record.refresh_token_display = record.refresh_token[:10] + '...'
#             else:
#                 record.refresh_token_display = ''

#     @api.model
#     def get_config(self):
#         config = self.search([], limit=1)
#         if not config:
#             config = self.create({
#                 'name': 'Configuración ISI-PASS',
#                 'shop_url': 'https://mitienda.com',
#                 'email': 'ejemplo@email.com',
#                 'password': 'contraseña_segura'
#             })
#         return config

#     def execute_login_mutation(self):
#         self.ensure_one()
#         mutation = """
#         mutation LOGIN {
#             login(shop: "%s", email: "%s", password: "%s") {
#                 token
#                 refreshToken
#                 perfil {
#                     nombres
#                     apellidos
#                     miEmpresa {
#                         razonSocial
#                         codigoModalidad
#                         codigoAmbiente
#                         fechaValidezToken
#                         tienda
#                         email
#                         emailFake
#                     }
#                     sucursal {
#                         codigo
#                         direccion
#                         telefono
#                         departamento {
#                             codigo
#                             codigoPais
#                             sigla
#                             departamento
#                         }
#                     }
#                 }
#             }
#         }
#         """ % (self.shop_url, self.email, self.password)

#         try:
#             response = requests.post(self.api_url, json={'query': mutation})
#             response_data = json.loads(response.text)
            
#             # Verificar si hay errores en la respuesta
#             if 'errors' in response_data:
#                 error_message = response_data['errors'][0]['message']
#                 if "verifique nombre urlComercio" in error_message:
#                     raise UserError("Error en la URL de Comercio. Por favor, verifique que el nombre y la URL de la tienda sean correctos.")
#                 else:
#                     raise UserError(f"Error al iniciar sesión: {error_message}")
            
#             # Si no hay errores, procesar los datos
#             data = response_data['data']['login']
#             if data is None:
#                 raise UserError("Error al iniciar sesión. Por favor, verifique sus credenciales.")
            
#             # Continuar con la lógica de almacenamiento de los tokens y datos del perfil
#             self.token = data['token']
#             self.refresh_token = data['refreshToken']
#             perfil = data['perfil']
#             self.nombres = perfil['nombres']
#             self.apellidos = perfil['apellidos']
#             empresa = perfil['miEmpresa']
#             self.razon_social = empresa['razonSocial']
#             self.codigo_modalidad = empresa['codigoModalidad']
#             self.codigo_ambiente = empresa['codigoAmbiente']
#             self.fecha_validez_token = empresa['fechaValidezToken']
#             self.tienda = empresa['tienda']
#             self.email_empresa = empresa['email']
#             self.email_fake = empresa['emailFake']
#             sucursal = perfil['sucursal']
#             self.sucursal_codigo = sucursal['codigo']
#             self.sucursal_direccion = sucursal['direccion']
#             self.sucursal_telefono = sucursal['telefono']
#             departamento = sucursal['departamento']
#             self.departamento_codigo = departamento['codigo']
#             self.departamento_codigo_pais = departamento['codigoPais']
#             self.departamento_sigla = departamento['sigla']
#             self.departamento_nombre = departamento['departamento']
#             return True
#         except UserError as ue:
#             raise ue
#         except Exception as e:
#             raise UserError(f"Error inesperado al ejecutar la mutación: {str(e)}")


#     def login(self):
#         self.ensure_one()
#         if self.execute_login_mutation():
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'reload',
#             }
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': 'Error de login',
#                 'message': 'No se pudo iniciar sesión. Por favor, verifica tus credenciales.',
#                 'sticky': False,
#                 'type': 'warning',
#             }
#         }
