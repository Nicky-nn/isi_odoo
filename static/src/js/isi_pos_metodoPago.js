/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useService } from "@web/core/utils/hooks";
import { CardNumberModal } from "./isi_card_number_modal"; // Modal para el número de tarjeta
import { ErrorModal } from "./isi_error_modal"; // Modal de error
import { SuccessModal } from "./isi_modal_api"; // Modal de éxito
import { _t } from "@web/core/l10n/translation"; // Para traducciones

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
        this.allowSiatCustomer = this.pos.config.allow_siat_customer;
    },

    // Helper function para verificar facturación obligatoria
    _requiresMandatoryInvoice() {
        const order = this.currentOrder;
        if (!order || typeof order.get_paymentlines !== "function") {
            console.error("Orden inválida o método get_paymentlines no disponible:", order);
            return false;
        }
        const paymentLines = order.get_paymentlines();
        return paymentLines.some(
            (line) => line.payment_method?.facturacion_obligatoria
        );
    },

    /**
     * @override
     */
    async addNewPaymentLine(event) {
        if (!this.allowSiatCustomer) return super.addNewPaymentLine(event);

        const paymentMethod = event?.detail || event;
        if (!paymentMethod) {
            console.error("Método de pago no válido:", paymentMethod);
            this.notification.add(_t("Método de pago no válido"), { type: "warning" });
            return;
        }

        const currentOrder = this.currentOrder;
        if (!currentOrder) {
            console.error("No hay orden actual:", currentOrder);
            this.notification.add(_t("No hay una orden activa"), { type: "warning" });
            return;
        }

        if (typeof currentOrder.get_paymentlines !== "function") {
            console.error("El método get_paymentlines no está definido en currentOrder:", currentOrder);
            this.notification.add(_t("Error interno: método no disponible"), { type: "danger" });
            return;
        }

        // Si es pago con tarjeta, mostrar el modal antes de añadir la línea
        if (paymentMethod.name.toLowerCase().includes("tarjeta")) {
            return new Promise((resolve, reject) => {
                this.dialogService.add(CardNumberModal, {
                    confirm: async (cardNumber) => {
                        try {
                            currentOrder.set_temporary_card_number(cardNumber);
                            console.log("Número de tarjeta guardado temporalmente:", cardNumber);

                            const newPaymentLine = await super.addNewPaymentLine(event);

                            if (newPaymentLine) {
                                if (this._requiresMandatoryInvoice()) {
                                    currentOrder.set_to_invoice(true);
                                    this.notification.add(
                                        _t("Uno de los métodos de pago requiere facturación"),
                                        { type: "info" }
                                    );
                                }
                                this.render();
                            }
                            resolve(newPaymentLine);
                        } catch (error) {
                            console.error("Error al procesar el pago con tarjeta:", error);
                            this.notification.add(
                                _t("Error al procesar el pago con tarjeta"),
                                { type: "warning" }
                            );
                            currentOrder.set_temporary_card_number(null);
                            reject(error);
                        }
                    },
                    close: () => {
                        resolve(null);
                    },
                });
            });
        } else {
            // Para otros métodos de pago
            if (currentOrder.get_paymentlines().length === 0) {
                currentOrder.set_temporary_card_number(null);
            }

            try {
                const newPaymentLine = await super.addNewPaymentLine(event);
                if (this._requiresMandatoryInvoice()) {
                    currentOrder.set_to_invoice(true);
                    this.notification.add(
                        _t("Uno de los métodos de pago requiere facturación"),
                        { type: "info" }
                    );
                }
                this.render();
                return newPaymentLine;
            } catch (error) {
                console.error("Error al procesar el pago:", error);
                this.notification.add(_t("Error al procesar el pago"), { type: "warning" });
            }
        }
    },

    /**
     * @override
     */
    async validateOrder(isForceValidate) {
        if (!this.allowSiatCustomer) {
            const result = await super.validateOrder(isForceValidate);
            if (this.currentOrder?.finalized) {
                this.dialogService.add(SuccessModal, {
                    orderName: this.currentOrder.name,
                    isInvoice: this.currentOrder.is_to_invoice(),
                });
            }
            return result;
        }

        const currentOrder = this.currentOrder;
        if (!currentOrder) {
            console.error("No hay orden actual para validar.");
            this.notification.add(_t("No hay una orden activa para validar"), { type: "warning" });
            return false;
        }

        if (this._requiresMandatoryInvoice()) {
            if (!currentOrder.is_to_invoice()) {
                currentOrder.set_to_invoice(true);
                this.notification.add(
                    _t("La facturación es obligatoria debido a uno de los métodos de pago."),
                    { type: "warning" }
                );
                this.render();
            }
            if (!currentOrder.get_partner()) {
                this.notification.add(
                    _t("Se requiere un cliente para la facturación obligatoria."),
                    { type: "warning" }
                );
                return false;
            }
        }

        if (!(currentOrder.is_paid_with_cash() || currentOrder.get_change() > 0)) {
            const total = currentOrder.get_total_with_tax();
            const paid = currentOrder.get_total_paid();
            if (Math.abs(total - paid) > currentOrder.pos.currency.rounding) {
                this.notification.add(
                    _t("El monto pagado debe ser igual al total."),
                    { type: "warning" }
                );
                return false;
            }
        }

        try {
            const result = await super.validateOrder(isForceValidate);
            if (this.currentOrder?.finalized) {
                this.dialogService.add(SuccessModal, {
                    title: _t("¡Procesado con Éxito!"),
                    orderName: this.currentOrder.name,
                    isInvoice: this.currentOrder.is_to_invoice(),
                });
            }
            return result;
        } catch (error) {
            console.error("Error durante la validación final:", error);
            this.dialogService.add(ErrorModal, {
                title: _t("Error al procesar la orden"),
                errorMessage: error?.data?.message || error?.message || _t("Error desconocido"),
            });
            return false;
        }
    },

    /**
     * @override
     */
    async render() {
        await super.render();
        if (!this.allowSiatCustomer) return;

        const currentOrder = this.currentOrder;
        if (!currentOrder) return;

        const requiresInvoice = this._requiresMandatoryInvoice();
        const invoiceButton = this.el?.querySelector(".js_invoice");
        if (!invoiceButton) return;

        if (requiresInvoice) {
            if (!currentOrder.is_to_invoice()) {
                currentOrder.set_to_invoice(true);
            }
            invoiceButton.classList.add("highlight", "checked");
            invoiceButton.title = _t("Facturación obligatoria por método de pago");
        } else {
            invoiceButton.title = "";
            if (!currentOrder.is_to_invoice()) {
                invoiceButton.classList.remove("checked");
            }
        }
    },
});