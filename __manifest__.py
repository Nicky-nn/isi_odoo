# -*- coding: utf-8 -*-
{
    'name': "isi-odoo-v2",

    'summary': "Conexión a la API de ISI_INVOICE para la facturación con SIAT",

    'description': """
        Módulo para conectar Odoo con la API de ISI_INVOICE,con SIAT.
    """,

    'author': "INTEGRATE Soluciones Informáticas",
    'website': "https://integrate.com.bo/",

    'category': 'Point of Sale',
    'version': '1.1.0',

    'depends': ['base', 'product', 'account', 'account_payment', 'sale', 'point_of_sale', 'hr'],

    'data': [
        #'security/ir.model.access.csv',
        'views/isi_homologado.xml',
        'views/templates.xml',
        'security/ir.model.access.csv',
        'views/isi_pass_views.xml',
        'views/isi_user_config.xml',
        'views/isi_clientes.xml',
        'views/isi_factura.xml',
        'views/sucursal_punto_venta_views.xml',
        'views/res_partner_views.xml',
        'views/isi_user_empleado.xml',
        'views/isi_metodoPago.xml',
        'views/isi_pos_cliente.xml',
        'views/pos.xml',
        'views/isi_diarios.xml',
        'views/isi_sucursal_pos.xml',
    ],
    "assets": {
        'point_of_sale._assets_pos': [
            'isiodoo/static/src/**/*'
        ]
    },
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    "images": ["static/description/banner.png"],
}
