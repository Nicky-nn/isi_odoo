# -*- coding: utf-8 -*-
# from odoo import http


# class Nick(http.Controller):
#     @http.route('/nick/nick', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/nick/nick/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('nick.listing', {
#             'root': '/nick/nick',
#             'objects': http.request.env['nick.nick'].search([]),
#         })

#     @http.route('/nick/nick/objects/<model("nick.nick"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('nick.object', {
#             'object': obj
#         })

