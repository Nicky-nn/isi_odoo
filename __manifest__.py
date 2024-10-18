# -*- coding: utf-8 -*-
{
    'name': "nick",

    'summary': "Conexión a la API de ISI_INVOICE para la facturación con SIAT",

    'description': """
        Módulo para conectar Odoo con la API de ISI_INVOICE, facilitando la integración 
        y automatización del proceso de facturación en cumplimiento con el Sistema 
        de Interoperabilidad de Autorización de Transacciones (SIAT).
    """,

    'author': "INTEGRATE Soluciones Informáticas",
    'website': "https://integrate.com.bo/",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base', 'product', 'account', 'account_payment', 'account_fleet', 'sale'],

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
    ],
    'assets': {
        "web.assets_backend": [
            "nick/static/src/**/*",
        ],
        "web.qunit_suite_tests": [
            "nick/static/tests/**/*",
        ],
        "point_of_sale.assets": [
            "nick/static/src/**/*",
        ],
    },
    'demo': [
        'demo/demo.xml',
    ],
}
