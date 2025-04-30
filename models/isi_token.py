from odoo import http
from odoo.http import request
import json
import requests

class WhatsappApiController(http.Controller):

    @http.route('/api/send_whatsapp', type='json', auth='user', methods=['POST'])
    def send_whatsapp(self):
        try:
            # Obtener el usuario actual
            current_user_id = request.env.user.id
            print(f"Usuario actual (ID): {current_user_id}")

            # Obtener token
            request.env.cr.execute("""
                SELECT token FROM isi_pass_config
                WHERE user_id = %s
                LIMIT 1
            """, (current_user_id,))
            token_result = request.env.cr.fetchone()
            token = token_result[0] if token_result else None

            if not token:
                print("Token no encontrado.")
                return {'error': 'Token no encontrado para el usuario actual.'}

            # Obtener URL de la API
            request.env.cr.execute("""
                SELECT api_url FROM isi_pass_config
                WHERE user_id = %s
                LIMIT 1
            """, (current_user_id,))
            api_url_result = request.env.cr.fetchone()
            print(f"Resultado de la URL de la API: {api_url_result}")
            api_url = api_url_result[0] if api_url_result else None

            if not api_url:
                print("URL de la API no encontrada.")
                return {'error': 'URL de la API no encontrada para el usuario actual.'}

            # Obtener los datos enviados en la solicitud
            try:
                # Si `jsonrequest` no está disponible, usar `httprequest.data`
                raw_data = request.httprequest.data.decode('utf-8')
                print(f"Datos brutos recibidos: {raw_data}")
                data = json.loads(raw_data)
            except Exception as e:
                print(f"Error al procesar los datos JSON: {str(e)}")
                return {'error': 'Error al procesar los datos JSON.'}

            print(f"Datos procesados: {data}")
            telefono = data.get('telefono')
            razon_social = data.get('razon_social', '')
            nit = data.get('nit', '')
            urlPDF = data.get('url_pdf', '').replace('"', '\\"')

            if not telefono or not urlPDF:
                print("Teléfono o URL del PDF faltante.")
                return {'error': 'El teléfono y la URL del PDF son obligatorios.'}

            # Construir el mensaje
            mensaje = f"""Estimado Sr(a) {razon_social},\\n\\nSe ha generado el presente documento fiscal de acuerdo al siguiente detalle:\\n\\nFACTURA COMPRA/VENTA\\n\\nRazón Social: {razon_social}\\nNIT/CI/CEX: {nit}\\n\\nSi recibiste este mensaje por error o tienes alguna consulta acerca de su contenido, comunícate con el remitente.\\n\\nAgradecemos tu preferencia.""".replace('"', '\\"').replace('\n', '\\n')
            print(f"Mensaje construido: {mensaje}")

            # Construir la mutación
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
            print(f"Mutación construida: {mutation}")

            # Configurar los encabezados
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            # Hacer la solicitud POST
            print(f"Enviando solicitud POST a {api_url}")
            response = requests.post(api_url, json={'query': mutation}, headers=headers)
            response_data = response.json()
            print(f"Respuesta de la API: {response_data}")

            # Manejo de errores
            if 'errors' in response_data:
                    error_message = response_data['errors'][0]['message']
                    print(f"Error devuelto por la API: {error_message}")
                    return {'error': "Error al enviar el mensaje."}

            if response.status_code == 200:
                print("Mensaje enviado correctamente.")
                return {'success': 'Mensaje enviado correctamente'}
            else:
                print(f"Error HTTP en la solicitud: {response.status_code} - {response.text}")
                return {'error': 'Error al enviar el mensaje.'}

        except Exception as e:
            print(f"Excepción capturada: {str(e)}")
            return {'error': str(e)}
