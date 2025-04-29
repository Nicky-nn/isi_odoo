/** @odoo-module **/


import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class ErrorModal extends Component {
    static template = "pos_order_error_modal";  // el t-name en tu XML
    static components = { Dialog };
    static props = {
        close: Function,
        title: { type: String, optional: true },
        errorMessage: String,
    };

    confirm() {
        this.props.close();
    }
}
