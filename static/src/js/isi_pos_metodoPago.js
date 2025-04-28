/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useService } from "@web/core/utils/hooks";
import { CardNumberModal } from "./isi_card_number_modal"; // El nuevo modal para el número de tarjeta
import { ErrorModal } from "./isi_error_modal"; // Modal de error
import { SuccessModal } from "./isi_modal_api"; // Modal de éxito
import { _t } from "@web/core/l10n/translation"; // Para traducciones

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
        // Quitamos el orm de aquí si solo se usaba para guardar la tarjeta
        // this.orm = useService("orm");
        this.allowSiatCustomer = this.pos.config.allow_siat_customer;
    },

    // Helper function (sin cambios)
    _requiresMandatoryInvoice() {
        const order = this.currentOrder;
        if (!order) return false;
        const paymentLines = order.get_paymentlines();
        return paymentLines.some(
            (line) => line.payment_method.facturacion_obligatoria
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
            /* ... manejo de error ... */ return;
        }
        const currentOrder = this.currentOrder;
        if (!currentOrder) {
            console.error("No hay orden actual:", currentOrder);
            /* ... manejo de error ... */ return;
        }

        // Si es pago con tarjeta, mostrar el modal ANTES de añadir la línea
        if (paymentMethod.name.toLowerCase().includes("tarjeta")) {
            return new Promise((resolve, reject) => {
                this.dialogService.add(CardNumberModal, {
                    confirm: async (cardNumber) => {
                        try {
                            // 1. Guardar temporalmente el número de tarjeta en la orden
                            currentOrder.set_temporary_card_number(cardNumber);
                            console.log(
                                "Número de tarjeta guardado temporalmente:",
                                cardNumber
                            );

                            // 2. Añadir la línea de pago (SIN borrar otras)
                            const newPaymentLine =
                                await super.addNewPaymentLine(event); // Llama al original

                            if (newPaymentLine) {
                                // 3. Verificar facturación obligatoria
                                if (this._requiresMandatoryInvoice()) {
                                    currentOrder.set_to_invoice(true);
                                    this.notification.add(
                                        _t(
                                            "Uno de los métodos de pago requiere facturación"
                                        ),
                                        { type: "info" }
                                    );
                                }
                                this.render(); // Actualizar UI
                            }
                            resolve(newPaymentLine);
                        } catch (error) {
                            console.error(
                                "Error al procesar el pago con tarjeta:",
                                error
                            );
                            this.notification.add(
                                _t("Error al procesar el pago con tarjeta"),
                                { type: "warning" }
                            );
                            currentOrder.set_temporary_card_number(null); // Limpiar en caso de error
                            reject(error);
                        }
                    },
                    close: () => {
                        resolve(null); // Resuelve null si el usuario cierra el modal sin confirmar
                    },
                });
            });
        } else {
            // Para otros métodos de pago (no tarjeta)
            // Limpiar el número de tarjeta temporal si se añade otro método que no sea tarjeta
            // (Podrías necesitar una lógica más compleja si permites múltiples tarjetas)
            if (currentOrder.get_paymentlines().length === 0) {
                // Si es la primera línea no-tarjeta
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
                this.notification.add(_t("Error al procesar el pago"), {
                    type: "warning",
                });
            }
        }
    },

    /**
     * @override
     */
    async validateOrder(isForceValidate) {
        if (!this.allowSiatCustomer) {
            // Llama al original y luego muestra el modal de éxito si la validación fue bien
            const result = await super.validateOrder(isForceValidate);
            // 'result' podría no ser estándar, la clave es que no haya error
            // La llamada a _finalizeValidation es la que realmente importa
            // El flujo normal del POS ya implica éxito si no hay excepción.
            // Podríamos mostrar el modal en _finalizeValidation o después de que la sincronización ocurra.
            // Para simplificar, lo ponemos aquí asumiendo que si super.validateOrder no falla, está bien.
            // PERO esto es antes de la sincronización completa.
            // Un mejor enfoque sería mostrar el modal DESPUÉS de que la orden se sincronice.

            // --- Inicio: Lógica Modal Éxito (Simple) ---
            // Esta es una simplificación. El éxito real es post-sincronización.
            if (this.currentOrder.finalized) {
                // Chequea si la orden se marcó como finalizada
                const order = this.currentOrder;
                this.dialogService.add(SuccessModal, {
                    orderName: order.name,
                    isInvoice: order.is_to_invoice(),
                });
            }
            // --- Fin: Lógica Modal Éxito ---

            return result; // Devuelve el resultado original
        }

        const currentOrder = this.currentOrder;
        if (!currentOrder) {
            /* ... manejo error ... */ return false;
        }

        // Verificar factura obligatoria y cliente
        if (this._requiresMandatoryInvoice()) {
            if (!currentOrder.is_to_invoice()) {
                currentOrder.set_to_invoice(true);
                this.notification.add(
                    _t(
                        "La facturación es obligatoria debido a uno de los métodos de pago."
                    ),
                    { type: "warning" }
                );
                this.render();
            }
            if (!currentOrder.get_partner()) {
                this.notification.add(
                    _t(
                        "Se requiere un cliente para la facturación obligatoria."
                    ),
                    { type: "warning" }
                );
                return false; // Impedir validación
            }
        }

        // Verificar monto total (sin cambios)
        if (
            !(currentOrder.is_paid_with_cash() || currentOrder.get_change() > 0)
        ) {
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

        // --- Inicio: Llamada a Validación Original y Modal Éxito ---
        try {
            // Llama a la validación original (envía al backend)
            const result = await super.validateOrder(isForceValidate);

            if (this.currentOrder.finalized) {
                this.dialogService.add(SuccessModal, {
                    title: _t("¡Procesado con Éxito!"),
                    orderName: this.currentOrder.name,
                    isInvoice: this.currentOrder.is_to_invoice(),
                });
            }
            return result;
        } catch (error) {
            console.error(
                "Error durante la validación final (Objeto Completo):",
                error
            ); // <-- AÑADE ESTO
            console.log(
                "Error al procesar la orden (Mensaje Intentado):",
                error?.data?.message || error?.message
            ); // Tu log original modificado con optional chaining

            // Mostramos el modal de error
            this.dialogService.add(ErrorModal, {
                title: _t("Error al procesar la orden"),
                errorMessage:
                    error?.data?.message || // Intenta obtener el mensaje específico de Odoo/Python primero
                    error?.message || // Si no, el mensaje genérico del error RPC
                    String(error) || // Como último recurso, convierte el objeto a string
                    _t("Error desconocido"),
            });
            return false;
        }
        // --- Fin: Llamada a Validación Original y Modal Éxito ---
    },

    /**
     * @override _onClickInvoice (Sin cambios significativos respecto a tu versión)
     */
    async _onClickInvoice(event) {
        // Añadido 'event' para preventDefault
        if (!this.allowSiatCustomer) return super._onClickInvoice();
        const currentOrder = this.currentOrder;
        if (!currentOrder) return;

        if (this._requiresMandatoryInvoice()) {
            if (!currentOrder.is_to_invoice()) {
                currentOrder.set_to_invoice(true);
            }
            this.notification.add(
                _t(
                    "La facturación es obligatoria debido a uno de los métodos de pago."
                ),
                { type: "warning" }
            );
            this.render();
            event?.preventDefault(); // Prevenir si el usuario intenta desmarcar
            event?.stopPropagation();
            return false; // No continuar con la lógica original de toggle
        } else {
            return super._onClickInvoice(); // Comportamiento normal
        }
    },

    /**
     * @override render (Sin cambios significativos respecto a tu versión, añadir _t para traducción)
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
                currentOrder.set_to_invoice(true); // Asegurar estado correcto
            }
            invoiceButton.classList.add("highlight", "checked"); // Forzar visualmente
            invoiceButton.title = _t(
                "Facturación obligatoria por método de pago"
            );
            // Considera deshabilitar el botón si no se puede cambiar
            // invoiceButton.setAttribute("disabled", "disabled");
        } else {
            // invoiceButton.removeAttribute("disabled"); // Quitar deshabilitado si se añadió
            invoiceButton.title = ""; // Limpiar tooltip
            // La clase 'checked' la maneja Odoo según is_to_invoice(), pero aseguramos quitarla si no aplica
            if (!currentOrder.is_to_invoice()) {
                invoiceButton.classList.remove("checked");
            }
            // Quitar highlight si no es obligatorio (Odoo base puede añadir 'highlight' si está activo)
            // invoiceButton.classList.remove("highlight"); // Quizás no sea necesario quitarlo siempre
        }
    },

    // ELIMINADO: Ya no necesitamos esta función aquí
    // async saveCardNumber(orderId, cardNumber) { ... }
});
