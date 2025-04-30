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
        this.accountMove = null;
        this.hasDocuments = false;

        if (this.pos) {
            const order = this.pos.get_order();
            const partner = order ? order.get_partner() : null;
            const phoneNumber = partner ? partner.mobile || partner.phone : "";
            this.state = useState({ phoneNumber });
            
            // Cargar los datos de la factura cuando se inicializa la pantalla
            if (order && order.server_id) {
                this.loadInvoiceData(order.server_id);
            }
        } else {
            console.error("POS environment is not available.");
            this.state = useState({ phoneNumber: "" });
        }
    },

    async loadInvoiceData(orderId) {
        try {
            this.accountMove = await this.getAccountMove(orderId);
            this.hasDocuments = !!this.accountMove;
        } catch (error) {
            console.error("Error loading invoice data:", error);
            this.hasDocuments = false;
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

    showDialog(title, body) {
        this.dialog.add(AlertDialog, {
            title: title,
            body: body,
        });
    },

    // Método para abrir URL en una nueva ventana
    openUrl(url) {
        if (url) {
            window.open(url, '_blank');
        } else {
            this.showDialog("Advertencia", "URL no disponible.");
        }
    },

    // Funciones para los nuevos botones
    async printPdf() {
        if (!this.accountMove || !this.accountMove.pdf_url) {
            this.showDialog("Advertencia", "El PDF no está disponible.");
            return;
        }
        
        try {
            this.uiService.block();
            // Abre el PDF para imprimir
            const printWindow = window.open(this.accountMove.pdf_url, '_blank');
            if (printWindow) {
                printWindow.addEventListener('load', function() {
                    printWindow.print();
                });
            }
            this.uiService.unblock();
        } catch (error) {
            console.error("Error al imprimir PDF:", error);
            this.uiService.unblock();
            this.showDialog("Error", "No se pudo imprimir el PDF.");
        }
    },

    async printRollo() {
        if (!this.accountMove || !this.accountMove.rollo_url) {
            this.showDialog("Advertencia", "El formato de rollo no está disponible.");
            return;
        }
        
        try {
            this.uiService.block();
            // Abre la versión de rollo para imprimir
            const printWindow = window.open(this.accountMove.rollo_url, '_blank');
            if (printWindow) {
                printWindow.addEventListener('load', function() {
                    printWindow.print();
                });
            }
            this.uiService.unblock();
        } catch (error) {
            console.error("Error al imprimir formato de rollo:", error);
            this.uiService.unblock();
            this.showDialog("Error", "No se pudo imprimir el formato de rollo.");
        }
    },

    viewSin() {
        if (!this.accountMove || !this.accountMove.sin_url) {
            this.showDialog("Advertencia", "La URL de SIN no está disponible.");
            return;
        }
        this.openUrl(this.accountMove.sin_url);
    },

    viewXml() {
        if (!this.accountMove || !this.accountMove.xml_url) {
            this.showDialog("Advertencia", "El XML no está disponible.");
            return;
        }
        this.openUrl(this.accountMove.xml_url);
    },

    async sendWhatsApp() {
        if (this.state.phoneNumber) {
            this.uiService.block();

            const order = this.pos.get_order();
            const partner = order ? order.get_partner() : null;
            
            // Asegurarse de que tenemos los datos de la factura actualizados
            if (!this.accountMove && order.server_id) {
                this.accountMove = await this.getAccountMove(order.server_id);
            }

            const payload = {
                telefono: this.state.phoneNumber,
                razon_social: partner ? partner.name : "",
                nit: partner ? partner.vat : "",
                url_pdf: this.accountMove ? this.accountMove.pdf_url : "",
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
                    this.showDialog("Error", data.result.error);
                } else {
                    this.showDialog("Mensaje enviado", "El mensaje de WhatsApp fue enviado correctamente.");
                }
            } catch (error) {
                console.error("Error al realizar la solicitud:", error);
                this.uiService.unblock();
                this.showDialog(
                    "Error",
                    "Ocurrió un error al enviar el mensaje de WhatsApp."
                );
            }
        } else {
            this.showDialog(
                "Advertencia",
                "El número de teléfono no está disponible."
            );
        }
    },
});