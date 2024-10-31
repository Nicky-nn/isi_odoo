/** @odoo-module */
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class ApiResponsePopup extends Component {
    static template = "api_bus.ApiResponsePopup";
    static defaultProps = {
        type: "error",
        title: "",
        body: "",
        urls: {},
    };

    setup() {
        // Cualquier lógica de inicialización adicional puede ir aquí
    }

    openUrl(url) {
        if (url) {
            window.open(url, "_blank");
        }
    }
}

export class ApiBusService {
    static serviceDependencies = ["orm", "bus_service", "popup"];

    constructor(...args) {
        this.setup(...args);
    }

    setup(env, { orm, bus_service, popup }) {
        this.orm = orm;
        this.popup = popup;

        // Canal de comunicación para respuestas de API
        bus_service.addChannel("api_response_channel");

        // Escuchar notificaciones
        bus_service.addEventListener("notification", ({ detail }) => {
            for (const message of detail) {
                this.dispatch(message);
            }
        });
    }

    dispatch(message) {
        // Verificar si el mensaje es para respuestas de API
        if (message.type === "api_response_channel") {
            // Mostrar popup según el tipo de respuesta
            this.showApiResponsePopup(message.payload);
        }
    }

    showApiResponsePopup(payload) {
        if (payload.payload.errors) {
            // Popup de error
            this.popup.add(ApiResponsePopup, {
                type: "error",
                title: payload.payload.errors[0].message.toUpperCase() || "Error",
                body: "",
            });
        } else if (
            payload.payload.data &&
            payload.payload.data.facturaCompraVentaCreate
        ) {
            // Popup de factura exitosa
            const factura = payload.payload.data.facturaCompraVentaCreate;
            const representacionGrafica = factura.representacionGrafica || {};

            this.popup.add(ApiResponsePopup, {
                type: "success",
                title: "Factura Generada Exitosamente",
                body: ``,
                urls: {
                    pdf: representacionGrafica.pdf,
                    rollo: representacionGrafica.rollo,
                    sin: representacionGrafica.sin,
                    xml: representacionGrafica.xml,
                },
            });
        }
    }
}

export const apiBusService = {
    dependencies: ApiBusService.serviceDependencies,
    async start(env, deps) {
        return new ApiBusService(env, deps);
    },
};

registry.category("services").add("api_bus", apiBusService);
