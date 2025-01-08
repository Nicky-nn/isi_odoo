/** @odoo-module **/

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        if (this.pos) {
            const order = this.pos.get_order();
            const partner = order ? order.get_partner() : null;
            const phoneNumber = partner ? (partner.mobile || partner.phone) : "";
            this.state = useState({ phoneNumber });
        } else {
            console.error("POS environment is not available.");
            this.state = useState({ phoneNumber: "" });
        }
    },

    sendWhatsApp() {
        if (this.state.phoneNumber) {
            console.log("Sending WhatsApp to:", this.state.phoneNumber);
        } else {
            console.error("Número de teléfono no disponible.");
        }
    },
});