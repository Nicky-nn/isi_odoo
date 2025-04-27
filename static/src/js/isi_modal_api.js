/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class SuccessModal extends Component {
    static template = "pos_order_success_modal"; // Nombre del template XML
    static components = { Dialog };
    static props = {
        close: Function,
        title: { type: String, optional: true },
        orderName: String,
        isInvoice: Boolean,
    };

    setup() {
        this.pos = usePos(); // Si necesitas acceso a datos del POS
    }

    confirm() {
        this.props.close(); // Cierra el modal
        // Puedes añadir lógica adicional aquí si es necesario al confirmar
    }
}