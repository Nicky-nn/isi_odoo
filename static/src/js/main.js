/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    // Guarda el número de tarjeta temporalmente
    set_temporary_card_number(number) {
        this.temporary_card_number = number;
    },
    get_temporary_card_number() {
        return this.temporary_card_number;
    },

    // Añade el número de tarjeta al JSON enviado al backend
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.temporary_card_number = this.get_temporary_card_number(); // Asegúrate que el nombre coincida con _order_fields en Python
        return json;
    },

    // Inicialización (opcional pero buena práctica)
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.temporary_card_number = json.temporary_card_number || null; // Si se recarga una orden
    },
});
