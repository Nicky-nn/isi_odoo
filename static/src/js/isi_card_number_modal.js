/** @odoo-module */
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CardNumberModal extends Component {
    setup() {
        this.state = {
            cardNumber: "",
            error: "",
            isValid: false
        };
        
        this.notification = useService("notification");
    }

    validateInput(event) {
        // Permitir solo números
        const value = event.target.value.replace(/\D/g, '');
        this.state.cardNumber = value;
        
        // Validar longitud
        if (value.length === 8) {
            this.state.isValid = true;
            this.state.error = "";
        } else {
            this.state.isValid = false;
            this.state.error = value.length > 8 ? "El número debe tener 8 dígitos" : "";
        }
    }

    handleKeyup(event) {
        if (event.key === 'Enter' && this.state.isValid) {
            this.confirm();
        }
    }

    async confirm() {
        if (!this.state.isValid) return;
        
        await this.props.confirm(this.state.cardNumber);
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}

CardNumberModal.template = 'point_of_sale.CardNumberModal';