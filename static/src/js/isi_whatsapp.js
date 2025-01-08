/** @odoo-module **/

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
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

    async sendWhatsApp() {
        if (this.state.phoneNumber) {
            const payload = {
                telefono: this.state.phoneNumber,
                razon_social: "Empresa de Prueba",
                nit: "123456789",
                url_pdf:
                    "https://consulta.isipass.com.bo/client/consulta/v1/7yzcs85FYJXFHd5h1C63Z5bLC3vnC6kCK94NT7bbVWkYX3REBReQWj9Amt1xyH5BLUp42KCeoPBTrWMGTKVe8VmkVJR629cNwtMHjpCLPo25oBmezZ6bJYanKAjYpd",
            };

            console.log("Enviando mensaje de WhatsApp con datos:", payload);

            try {
                const response = await fetch("/api/send_whatsapp", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(payload),
                });

                const data = await response.json();
                console.log("Respuesta del servidor:", data);

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
