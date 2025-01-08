/** @odoo-module **/

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.state = useState({ phoneNumber: "+591 78812548" });
    },

    sendWhatsApp() {
        // Implement your WhatsApp sending logic here
        console.log("Sending WhatsApp to:", this.state.phoneNumber);
    },
});