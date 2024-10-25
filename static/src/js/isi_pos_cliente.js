/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";

patch(PartnerDetailsEdit.prototype, {
    setup() {
        super.setup();
        const partner = this.props.partner;
        // Initialize fields
        this.changes = {
            name: partner.name || "",
            mobile: partner.mobile || "",
            street: partner.street || "", // Recuperar el valor de la calle
            city: partner.city || "", // Recuperar el valor de la ciudad
            zip: partner.zip || "", // Recuperar el código postal
            email: partner.email || "",
            phone: partner.phone || "",
            barcode: partner.barcode || "",
            state_id: partner.state_id || "",
            codigo_tipo_documento_identidad:
                partner.codigo_tipo_documento_identidad || "",
            complemento: partner.complemento || "",
            razon_social: partner.razon_social || "",
            vat: partner.vat || "",
        };

        // Solo inicializar campos SIAT si están permitidos
        if (this.showSiatFields) {
            Object.assign(this.changes, {
                codigo_tipo_documento_identidad:
                    partner.codigo_tipo_documento_identidad || "",
                complemento: partner.complemento || "",
                razon_social: partner.razon_social || "",
                vat: partner.vat || "",
            });
        }

        // Datos estáticos de tipos de documento (solo si SIAT está activo)
        if (this.showSiatFields) {
            this.documentTypes = [
                {
                    codigoClasificador: "1",
                    descripcion: "CI - CEDULA DE IDENTIDAD",
                },
                {
                    codigoClasificador: "2",
                    descripcion: "CEX - CEDULA DE IDENTIDAD DE EXTRANJERO",
                },
                {
                    codigoClasificador: "5",
                    descripcion: "NIT - NÚMERO DE IDENTIFICACIÓN TRIBUTARIA",
                },
                { codigoClasificador: "3", descripcion: "PAS - PASAPORTE" },
                {
                    codigoClasificador: "4",
                    descripcion: "OD - OTRO DOCUMENTO DE IDENTIDAD",
                },
            ];
        }
    },

    get showSiatFields() {
        return this.pos.config.allow_siat_customer;
    },

    async saveChanges() {
        if (this.showSiatFields) {
            // Solo validar campos SIAT si están activos
            const requiredFields = [
                "name",
                "vat",
                "codigo_tipo_documento_identidad",
            ];
            for (const field of requiredFields) {
                if (!this.changes[field] && !this.props.partner[field]) {
                    this.changes[field] = false;
                }
            }

            // Asegurar que los campos SIAT estén incluidos
            const siatFields = [
                "codigo_tipo_documento_identidad",
                "complemento",
                "razon_social",
            ];
            for (const field of siatFields) {
                if (this.changes[field] === undefined) {
                    this.changes[field] = this.props.partner[field] || "";
                }
            }

            // Procesar el tipo de documento seleccionado
            if (this.changes.codigo_tipo_documento_identidad) {
                const selectedType = this.documentTypes.find(
                    (type) =>
                        type.codigoClasificador ===
                        this.changes.codigo_tipo_documento_identidad
                );
                if (selectedType) {
                    this.changes.codigo_tipo_documento_identidad =
                        selectedType.codigoClasificador;
                }
            }
        }

        // Siempre establecer estos campos como strings vacíos
        this.changes.state_id = "";
        this.changes.country_id = "";

        await super.saveChanges();
    },
});
