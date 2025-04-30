/** @odoo-module **/

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";


patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.uiService = useService('ui');
        this.dialog = useService("dialog");
        this.pos = usePos();
        if (this.pos) {
            const order = this.pos.get_order();
            const partner = order ? order.get_partner() : null;
            const phoneNumber = partner ? partner.mobile || partner.phone : "";
            this.state = useState({ phoneNumber });
        } else {
            console.error("POS environment is not available.");
            this.state = useState({ phoneNumber: "" });
        }
    },
    async getAccountMove(orderId) {
        try {
            const [orderWithInvoice] = await this.orm.read(
                "pos.order",
                [orderId],
                ["account_move"],
                { load: false }
            );

            if (orderWithInvoice?.account_move) {
                const [accountMove] = await this.orm.read(
                    "account.move",
                    [orderWithInvoice.account_move],
                    [
                        "id",
                        "name",
                        "date",
                        "amount_total",
                        "partner_id",
                        "state",
                        "cuf",
                        "pdf_url",
                        "sin_url",
                        "rollo_url",
                        "xml_url",
                    ]
                );
                return accountMove || null;
            } else {
                return null;
            }
        } catch (error) {
            console.error(
                "Error fetching account move:",
                error.message,
                error.stack
            );
            return null;
        }
    },

    async sendWhatsApp() {
        if (this.state.phoneNumber) {
            this.uiService.block();

            const order = this.pos.get_order();
            const partner = order ? order.get_partner() : null;
            const accountMove = await this.getAccountMove(order.server_id);
            console.log("Account Move:", accountMove);

            const payload = {
                telefono: this.state.phoneNumber,
                razon_social: partner ? partner.name : "",
                nit: partner ? partner.vat : "",
                url_pdf: accountMove ? accountMove.pdf_url : "",
            };

            try {
                const response = await fetch("/api/send_whatsapp", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(payload),
                });

                const data = await response.json();

                this.uiService.unblock();

                if (data.result.error) {
                    this.dialog.add(AlertDialog, {
                        title: "Error",
                        body: data.result.error,
                    });
                } else {
                    this.dialog.add(AlertDialog, {
                        title: "Mensaje enviado",
                        body: "El mensaje de WhatsApp fue enviado correctamente.",
                    });
                }
            } catch (error) {
                console.error("Error al realizar la solicitud:", error);
                this.showDialog(
                    "Error",
                    "Ocurrió un error al enviar el mensaje de WhatsApp."
                );
            }
        } else {
            console.error("Número de teléfono no disponible.");
            this.showDialog(
                "Advertencia",
                "El número de teléfono no está disponible."
            );
        }
    },
});
