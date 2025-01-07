/** @odoo-module **/

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { registry } from "@web/core/registry";

const patchReceiptScreen = (ReceiptScreen) => class extends ReceiptScreen {
    static template = "pos_receipt_invoice_send_whatsapp.ReceiptScreen";

    setup() {
        super.setup();
        this.orderUiState.phone_number = '';
        this.sendWhatsApp = this.sendWhatsApp.bind(this);
    }

    sendWhatsApp() {
        const phone = this.orderUiState.phone_number;
        console.log("Número de teléfono:", phone);
    }
};

registry.category("pos_receipt_screens").add("ReceiptScreen", patchReceiptScreen);