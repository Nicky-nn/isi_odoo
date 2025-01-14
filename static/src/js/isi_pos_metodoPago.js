/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useService } from "@web/core/utils/hooks";
import { CardNumberModal } from "./isi_card_number_modal";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
        this.allowSiatCustomer = this.pos.config.allow_siat_customer;
    },

    /**
     * @override
     */
    async addNewPaymentLine(event) {
        // Si allowSiatCustomer es false, obviar todo el código
        if (!this.allowSiatCustomer) return super.addNewPaymentLine(event);

        const paymentMethod = event?.detail || event;

        if (!paymentMethod) {
            this.notification.add("Error: Método de pago no válido", {
                type: "warning",
            });
            return;
        }

        const currentOrder = this.currentOrder;
        if (!currentOrder) {
            this.notification.add("No hay una orden activa", {
                type: "warning",
            });
            return;
        }

        // Si es pago con tarjeta, mostrar el modal antes de procesar
        if (paymentMethod.name.toLowerCase().includes("tarjeta")) {
            return new Promise((resolve, reject) => {
                this.dialogService.add(CardNumberModal, {
                    confirm: async (cardNumber) => {
                        try {
                            // Eliminar líneas de pago existentes
                            const existingPaymentLines =
                                currentOrder.get_paymentlines();
                            existingPaymentLines.forEach((line) => {
                                currentOrder.remove_paymentline(line);
                            });

                            const newPaymentLine =
                                await super.addNewPaymentLine(event);

                            if (newPaymentLine) {
                                currentOrder.set_to_invoice(true);
                                const orderId = currentOrder.server_id;
                                await this.savePhoneNumber(orderId, cardNumber);
                                this.render();

                                this.notification.add(
                                    "Pago con " +
                                        paymentMethod.name +
                                        " requiere facturación",
                                    {
                                        type: "info",
                                    }
                                );
                            }

                            resolve(newPaymentLine);
                        } catch (error) {
                            console.error("Error al procesar el pago:", error);
                            this.notification.add("Error al procesar el pago", {
                                type: "warning",
                            });
                            reject(error);
                        }
                    },
                    close: () => {
                        resolve(null);
                    },
                });
            });
        }

        // Eliminar líneas de pago existentes
        const existingPaymentLines = currentOrder.get_paymentlines();
        existingPaymentLines.forEach((line) => {
            currentOrder.remove_paymentline(line);
        });

        try {
            const newPaymentLine = await super.addNewPaymentLine(event);

            // Si es tarjeta, activar facturación obligatoria
            if (paymentMethod.facturacion_obligatoria) {
                currentOrder.set_to_invoice(true);
                this.render();

                this.notification.add(
                    "Pago con " + paymentMethod.name + " requiere facturación",
                    {
                        type: "info",
                    }
                );
            }

            return newPaymentLine;
        } catch (error) {
            console.error("Error al procesar el pago:", error);
            this.notification.add("Error al procesar el pago", {
                type: "warning",
            });
        }
    },

    /**
     * @override
     */
    async validateOrder(isForceValidate) {
        // Si allowSiatCustomer es false, obviar todo el código
        if (!this.allowSiatCustomer)
            return super.validateOrder(isForceValidate);

        const currentOrder = this.currentOrder;
        if (!currentOrder) {
            this.notification.add("No hay una orden activa para validar", {
                type: "warning",
            });
            return false;
        }

        const selectedPaymentLine = currentOrder.selected_paymentline;
        if (!selectedPaymentLine) {
            this.notification.add("Por favor seleccione un método de pago", {
                type: "warning",
            });
            return false;
        }

        // Verificar si es pago con tarjeta
        const isCard =
            selectedPaymentLine.payment_method?.facturacion_obligatoria;
        if (isCard) {
            currentOrder.set_to_invoice(true);
            this.render();
        }

        // Verificar monto total
        const total = currentOrder.get_total_with_tax();
        const paid = currentOrder.get_total_paid();
        if (Math.abs(total - paid) > 0.000001) {
            this.notification.add("El monto pagado debe ser igual al total", {
                type: "warning",
            });
            return false;
        }

        return super.validateOrder(isForceValidate);
    },

    /**
     * @override
     */
    async _onClickInvoice() {
        // Si allowSiatCustomer es false, obviar todo el código
        if (!this.allowSiatCustomer) return super._onClickInvoice();

        const currentOrder = this.currentOrder;
        if (!currentOrder) return;

        const selectedPaymentLine = currentOrder.selected_paymentline;
        if (!selectedPaymentLine) return;

        // Verificar si es pago con tarjeta
        const isCard =
            selectedPaymentLine.payment_method?.facturacion_obligatoria;

        if (isCard) {
            // Prevenir cualquier intento de desactivar la facturación
            currentOrder.set_to_invoice(true);
            this.render();
            this.notification.add(
                "El pago con tarjeta requiere facturación obligatoria",
                {
                    type: "warning",
                }
            );
            event?.preventDefault();
            event?.stopPropagation();
            return false;
        }

        // Para otros métodos de pago, comportamiento normal
        return super._onClickInvoice();
    },

    /**
     * Override del método render para asegurar que el estado de facturación se mantenga
     * @override
     */
    async render() {
        // Si allowSiatCustomer es false, obviar todo el código
        if (!this.allowSiatCustomer) return super.render();

        await super.render();

        // Verificar si hay un pago con tarjeta después del render
        const currentOrder = this.currentOrder;
        if (!currentOrder) return;

        const selectedPaymentLine = currentOrder.selected_paymentline;
        if (!selectedPaymentLine) return;

        const isCard =
            selectedPaymentLine.payment_method?.facturacion_obligatoria;
        if (isCard) {
            // Forzar el estado de facturación después del render
            currentOrder.set_to_invoice(true);

            // Intentar actualizar el botón de factura si está disponible
            const invoiceButton = this.el?.querySelector(".js_invoice");
            if (invoiceButton) {
                invoiceButton.classList.add("highlight", "checked");
                invoiceButton.setAttribute("disabled", "disabled");
            }
        }
    },

    async savePhoneNumber(orderId, cardNumber) {
        try {
            await this.orm.write("pos.order", [orderId], {
                numero_tarjeta: cardNumber,
            });
        } catch (error) {
            console.error("Error al guardar el número de teléfono:", error);
        }
    },
});
