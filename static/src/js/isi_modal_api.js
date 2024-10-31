/** @odoo-module */

import { registry } from "@web/core/registry";

export class ApiBusService {
    static serviceDependencies = ["orm", "bus_service"];

    constructor(...args) {
        this.setup(...args);
    }

    setup(env, { orm, bus_service }) {
        this.orm = orm;

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
