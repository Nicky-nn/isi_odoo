/** @odoo-module */
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

// Definir un popup personalizado siguiendo la estructura de Odoo
export class ApiResponsePopup extends Component {
    static template = "api_bus.ApiResponsePopup";
    static defaultProps = {
        title: "Respuesta de API",
        body: "",
    };

    setup() {
        // Cualquier lógica de inicialización adicional puede ir aquí
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

        console.log("Inicializando servicio de bus para API...");
        console.log("Canal de notificaciones: notification");
        console.log("Mensaje de respuesta de API: ", "api_response");

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
            console.log("----------------------------------------");
            console.log("Respuesta de la API:");
            console.log(message.payload);
            console.log("----------------------------------------");

            // Mostrar popup con la respuesta de la API
            this.showApiResponsePopup(message.payload);
        }
    }

    showApiResponsePopup(payload) {
        // Usar el servicio de popup para mostrar el mensaje
        this.popup.add(ApiResponsePopup, {
            title: "Respuesta de API",
            body: JSON.stringify(payload, null, 2)
        });
    }
}

export const apiBusService = {
    dependencies: ApiBusService.serviceDependencies,
    async start(env, deps) {
        return new ApiBusService(env, deps);
    },
};

registry.category("services").add("api_bus", apiBusService);