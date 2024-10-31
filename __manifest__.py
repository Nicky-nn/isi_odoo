# -*- coding: utf-8 -*-
{
    'name': "nick",

    'summary': "Conexión a la API de ISI_INVOICE para la facturación con SIAT",

    'description': """
        Módulo para conectar Odoo con la API de ISI_INVOICE,con SIAT.
    """,

    'author': "INTEGRATE Soluciones Informáticas",
    'website': "https://integrate.com.bo/",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base', 'product', 'account', 'account_payment', 'account_fleet', 'sale', 'point_of_sale', 'bus'],

    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'security/ir.model.access.csv',
        'views/isi_pass_views.xml',
        'views/isi_user_config.xml',
        'views/isi_clientes.xml',
        'views/isi_factura.xml',
        'views/isi_sucursal.xml',
        'views/sucursal_punto_venta_views.xml',
        'views/res_partner_views.xml',
        'views/isi_user_empleado.xml',
        'views/isi_metodoPago.xml',
        'views/isi_pos_cliente.xml',
        'views/pos.xml',
    ],
    "assets": {
        'point_of_sale._assets_pos': [
            'nick/static/src/**/*'
        ]
    },
    'demo': [
        'demo/demo.xml',
    ],
}
