from odoo import models, fields, api
import requests

# State: Completed
# Índice de la clase ResPartner
# Clase: ResPartner
# - Atributos:
#   - codigo_tipo_documento_identidad: Campo de selección para almacenar el tipo de documento de identidad del cliente.
#   - razon_social: Campo de texto que almacena la razón social del cliente.
#   - complemento: Campo de texto para información adicional del cliente.
#
# - Métodos:
#   - _onchange_name: Método que actualiza la razón social cuando se cambia el nombre del cliente.
#   - create: Método que crea un nuevo registro de cliente, asignando la razón social basada en el nombre proporcionado.
#   - write: Método que actualiza un registro de cliente y asigna la razón social si se ha cambiado el nombre.
#   - _get_document_type_selection: Método que obtiene los tipos de documentos de identidad desde una API externa y devuelve una lista de selección.
#   - obtener_tipo_documento_descripcion: Método que devuelve la descripción del tipo de documento según su código proporcionado.

class ResPartner(models.Model):
    _inherit = 'res.partner'

    codigo_tipo_documento_identidad = fields.Selection(
        selection=lambda self: self._get_document_type_selection(),
        string='Código Tipo de Documento de Identidad'
    )

    razon_social = fields.Char(string='Razón Social', readonly=False)
    complemento = fields.Char(string='Complemento')

    @api.onchange('name')
    def _onchange_name(self):
        # Actualiza la razón social cuando se cambia el nombre del cliente.
        if self.name:
            self.razon_social = self.name

    @api.model
    def create(self, vals):
        # Crea un nuevo registro de cliente y asigna la razón social basada en el nombre proporcionado.
        if 'name' in vals:
            vals['razon_social'] = vals['name']
        return super(ResPartner, self).create(vals)

    def write(self, vals):
        # Actualiza el registro de cliente y asigna la razón social si se ha cambiado el nombre.
        if 'name' in vals:
            vals['razon_social'] = vals['name']
        return super(ResPartner, self).write(vals)

    @api.model
    def _get_document_type_selection(self):
        # Obtiene los tipos de documentos de identidad desde una API externa.
        # Devuelve una lista de tuplas que contienen el código y la descripción del tipo de documento.
        api_model = self.env['document.identity.api']
        tipos_documento = api_model.get_document_types()
        return [(tipo.get('codigoClasificador'), tipo.get('descripcion')) for tipo in tipos_documento] if tipos_documento else []

    @api.model
    def obtener_tipo_documento_descripcion(self, codigo_tipo_documento_identidad):
        # Devuelve la descripción del tipo de documento según su código proporcionado.
        # Retorna None si no se encuentra el código.
        api_model = self.env['document.identity.api']
        tipos_documento = api_model.get_document_types()
        for tipo_documento in tipos_documento:
            if tipo_documento.get('codigoClasificador') == codigo_tipo_documento_identidad:
                return tipo_documento.get('descripcion')
        return None

# Índice de la clase DocumentIdentityAPI
# Clase: DocumentIdentityAPI
# - Métodos:
#   - get_token_for_user: Recupera el token de autenticación del usuario actual desde la base de datos.
#   - get_document_types: Obtiene los tipos de documentos de identidad desde la API externa utilizando el token de autenticación.

class DocumentIdentityAPI(models.TransientModel):
    _name = 'document.identity.api'
    _description = 'Consulta API para Tipos de Documentos de Identidad'

    @api.model
    def get_token_for_user(self):
        # Recupera el token de autenticación del usuario actual desde la base de datos.
        # Retorna el token si se encuentra, o None si no hay token disponible.
        current_user_id = self.env.user.id
        self.env.cr.execute("""
            SELECT token FROM isi_pass_config
            WHERE user_id = %s
            LIMIT 1
        """, (current_user_id,))
        result = self.env.cr.fetchone()
        if result:
            return result[0]
        return None

    @api.model
    def get_document_types(self):
        # Obtiene los tipos de documentos de identidad desde la API externa utilizando el token de autenticación.
        # Retorna una lista de tipos de documentos o una lista vacía si hay un error.
        token = self.get_token_for_user()
        if not token:
            return []

        self.env.cr.execute("""
            SELECT api_url FROM isi_pass_config
            WHERE user_id = %s
            LIMIT 1
        """, (self.env.user.id,))
        result = self.env.cr.fetchone()
        if not result:
            return []

        api_url = result[0]

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        query = """
        query TIPOS_DOCUMENTO_IDENTIDAD {
            sinTipoDocumentoIdentidad {
                codigoClasificador
                descripcion
            }
        }
        """

        try:
            response = requests.post(
                api_url, headers=headers, json={'query': query})
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('sinTipoDocumentoIdentidad', [])
            else:
                return []
        except requests.exceptions.RequestException:
            return []
