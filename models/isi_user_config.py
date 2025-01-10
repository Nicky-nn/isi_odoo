from odoo import api, fields, models
import requests
import json
import hashlib

from odoo.exceptions import UserError

# State: Completed
class ISIPassConfig(models.Model):
    # Modelo que almacena la configuración de ISI-PASS para un usuario.
    # Contiene campos para almacenar credenciales de inicio de sesión y datos de perfil.

    # Atributos:
    # - user_id: Campo de relación para almacenar el ID del usuario.
    # - employee_id: Campo de relación para almacenar el ID del empleado.
    # - name: Campo de texto para almacenar el nombre de la configuración.
    # - environment: Campo de selección para almacenar el entorno (sandbox o producción).
    # - api_url: Campo de texto para almacenar la URL de la API.
    # - shop_url: Campo de texto para almacenar la URL del comercio.
    # - email: Campo de texto para almacenar el correo electrónico.
    # - password: Campo de texto para almacenar la contraseña.
    # - token: Campo de texto para almacenar el token de autenticación.
    # - token_display: Campo calculado para mostrar una parte del token.
    # - refresh_token: Campo de texto para almacenar el token de actualización.
    # - refresh_token_display: Campo calculado para mostrar una parte del token de actualización.
    # - nombres: Campo de texto para almacenar los nombres del perfil.

    # Métodos:
    # - default_get(fields): Obtiene los valores por defecto de los campos.
    # - _onchange_environment(): Actualiza la URL de la API al cambiar el entorno.
    # - _compute_avatar(): Calcula la URL del avatar del usuario.
    # - _compute_token_display(): Calcula la parte visible del token.
    # - _compute_refresh_token_display(): Calcula la parte visible del token de actualización.
    # - get_config(user_id): Obtiene la configuración de ISI-PASS para un usuario.
    # - execute_login_mutation(): Ejecuta la mutación de inicio de sesión en la API.
    # - login(): Inicia sesión en la API y actualiza los campos de perfil.

    _name = 'isi.pass.config'
    _description = 'Configuración de ISI-PASS'

    # Campos como antes
    user_id = fields.Many2one(
        'res.users', string='Usuario', ondelete='cascade')
    employee_id = fields.Many2one(
        'hr.employee', string='Empleado', ondelete='cascade')
    name = fields.Char('Nombre', required=True)
    environment = fields.Selection([
        ('sandbox', 'Sandbox'),
        ('production', 'Producción')
    ], string='Entorno', required=True, default='sandbox')
    api_url = fields.Char('URL de API', required=True)
    shop_url = fields.Char('URL de Comercio', required=True)
    email = fields.Char('Correo Electrónico', required=True)
    password = fields.Char('Contraseña', required=True)
    token = fields.Char('Token', readonly=True)
    token_display = fields.Char(
        'Token Display', compute='_compute_token_display')
    refresh_token = fields.Char('Refresh Token', readonly=True)
    refresh_token_display = fields.Char(
        'Refresh Token Display', compute='_compute_refresh_token_display')
    nombres = fields.Char('Nombres', readonly=True)
    apellidos = fields.Char('Apellidos', readonly=True)
    avatar = fields.Char('Avatar URL', compute='_compute_avatar', store=True)
    razon_social = fields.Char('Razón Social', readonly=True)
    codigo_modalidad = fields.Char('Código Modalidad', readonly=True)
    codigo_ambiente = fields.Char('Código Ambiente', readonly=True)
    fecha_validez_token = fields.Char('Fecha Validez Token', readonly=True)
    tienda = fields.Char('Tienda', readonly=True)
    email_empresa = fields.Char('Email Empresa', readonly=True)
    email_fake = fields.Char('Email Fake', readonly=True)
    sucursal_codigo = fields.Char('Código Sucursal', readonly=True)
    sucursal_direccion = fields.Char('Dirección Sucursal', readonly=True)
    sucursal_telefono = fields.Char('Teléfono Sucursal', readonly=True)
    departamento_codigo = fields.Char('Código Departamento', readonly=True)
    departamento_codigo_pais = fields.Char('Código País', readonly=True)
    departamento_sigla = fields.Char('Sigla Departamento', readonly=True)
    departamento_nombre = fields.Char('Nombre Departamento', readonly=True)
    punto_venta_codigo = fields.Char('Código Punto de Venta', readonly=True)
    punto_venta_nombre = fields.Char('Nombre Punto de Venta', readonly=True)
    punto_venta_descripcion = fields.Char(
        'Descripción Punto de Venta', readonly=True)

    @api.model
    def default_get(self, fields):
        res = super(ISIPassConfig, self).default_get(fields)
        if self.env.context.get('default_employee_id'):
            employee = self.env['hr.employee'].browse(
                self.env.context['default_employee_id'])
            if employee.user_id:
                res['user_id'] = employee.user_id.id
        return res

    @api.onchange('environment')
    def _onchange_environment(self):
        if self.environment == 'sandbox':
            self.api_url = 'https://sandbox.isipass.net/api'
        elif self.environment == 'production':
            self.api_url = 'https://api.isipass.com.bo/api'

    @api.depends('email')
    def _compute_avatar(self):
        for record in self:
            if record.email:
                hash = hashlib.md5(record.email.lower().encode()).hexdigest()
                record.avatar = "https://gravatar.com/avatar/481d0f1df938bc2cbb04a3ea6285886f?s=400&d=robohash&r=x"
            else:
                record.avatar = "https://gravatar.com/avatar/481d0f1df938bc2cbb04a3ea6285886f?s=400&d=robohash&r=x"


    @api.depends('token')
    def _compute_token_display(self):
        for record in self:
            if record.token:
                record.token_display = record.token[:10] + '...'
            else:
                record.token_display = ''

    @api.depends('refresh_token')
    def _compute_refresh_token_display(self):
        for record in self:
            if record.refresh_token:
                record.refresh_token_display = record.refresh_token[:10] + '...'
            else:
                record.refresh_token_display = ''

    @api.model
    def get_config(self, user_id):
        config = self.search([('user_id', '=', user_id)], limit=1)
        if not config:
            config = self.create({
                'user_id': user_id,
                'shop_url': 'https://mitienda.com',
                'email': 'ejemplo@email.com',
                'password': 'contraseña_segura',
                'api_url': 'https://sandbox.isipass.net/api'  # Valor por defecto
            })
        return config

    def execute_login_mutation(self):
        self.ensure_one()
        mutation = """ mutation LOGIN {
            login(shop: "%s", email: "%s", password: "%s") {
                token
                refreshToken
                perfil {
                    nombres
                    apellidos
                    miEmpresa {
                        razonSocial
                        codigoModalidad
                        codigoAmbiente
                        fechaValidezToken
                        tienda
                        email
                        emailFake
                    }
                    sucursal {
                        codigo
                        direccion
                        telefono
                        departamento {
                            codigo
                            codigoPais
                            sigla
                            departamento
                        }
                    }
                    puntoVenta {
                        codigo
                        nombre
                        descripcion
                    }
                }
            }
        } """ % (self.shop_url, self.email, self.password)
        try:
            response = requests.post(self.api_url, json={'query': mutation})
            response_data = json.loads(response.text)
            if 'errors' in response_data:
                error_message = response_data['errors'][0]['message']
                if "verifique nombre urlComercio" in error_message:
                    raise UserError(
                        "Error en la URL de Comercio. Por favor, verifique que el nombre y la URL de la tienda sean correctos.")
                else:
                    raise UserError(
                        f"Error al iniciar sesión: {error_message}")
            data = response_data['data']['login']
            if data is None:
                raise UserError(
                    "Error al iniciar sesión. Por favor, verifique sus credenciales.")
            self.token = data['token']
            self.refresh_token = data['refreshToken']
            perfil = data['perfil']
            self.nombres = perfil['nombres']
            self.apellidos = perfil['apellidos']
            empresa = perfil['miEmpresa']
            self.razon_social = empresa['razonSocial']
            self.codigo_modalidad = empresa['codigoModalidad']
            self.codigo_ambiente = empresa['codigoAmbiente']
            self.fecha_validez_token = empresa['fechaValidezToken']
            self.tienda = empresa['tienda']
            self.email_empresa = empresa['email']
            self.email_fake = empresa['emailFake']
            sucursal = perfil['sucursal']
            self.sucursal_codigo = sucursal['codigo']
            self.sucursal_direccion = sucursal['direccion']
            self.sucursal_telefono = sucursal['telefono']
            departamento = sucursal['departamento']
            self.departamento_codigo = departamento['codigo']
            self.departamento_codigo_pais = departamento['codigoPais']
            self.departamento_sigla = departamento['sigla']
            self.departamento_nombre = departamento['departamento']
            punto_venta = perfil.get('puntoVenta', {})
            self.punto_venta_codigo = punto_venta.get('codigo')
            self.punto_venta_nombre = punto_venta.get('nombre')
            self.punto_venta_descripcion = punto_venta.get('descripcion')

            return True
        except UserError as ue:
            raise ue
        except Exception as e:
            raise UserError(
                f"Error inesperado al ejecutar la mutación: {str(e)}")

    def login(self):
        self.ensure_one()
        if self.execute_login_mutation():
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Error de login',
                'message': 'No se pudo iniciar sesión. Por favor, verifica tus credenciales.',
                'sticky': False,
                'type': 'warning',
            }
        }


class ResUsers(models.Model):

    # Atributos:
    # - isi_pass_config_id: Campo de relación para almacenar la configuración ISI-PASS del usuario.

    _inherit = 'res.users'
    isi_pass_config_id = fields.One2many(
        'isi.pass.config', 'user_id', string='Configuración ISI-PASS')
