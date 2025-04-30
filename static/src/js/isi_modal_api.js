/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class SuccessModal extends Component {
    static template = "point_of_sale.SuccessModal";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        orderName: { type: String, optional: true },
        isInvoice: { type: Boolean, optional: true },
        pdfUrl: { type: String, optional: true },
        xmlUrl: { type: String, optional: true },
        sinUrl: { type: String, optional: true },
        rolloUrl: { type: String, optional: true },
        close: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({
            title: this.props.title || _t("¡Éxito!"),
            orderName: this.props.orderName || "",
            isInvoice: this.props.isInvoice || false,
            message: this.props.isInvoice 
                ? _t("Orden facturada correctamente") 
                : _t("Orden procesada correctamente"),
        });
        
        // Definimos las URLs como propiedades simples (no reactivas)
        this.pdfUrl = this.props.pdfUrl || null;
        this.xmlUrl = this.props.xmlUrl || null;
        this.sinUrl = this.props.sinUrl || null;
        this.rolloUrl = this.props.rolloUrl || null;
        
        // Verificamos si hay alguna URL disponible
        this.hasUrls = !!(this.pdfUrl || this.xmlUrl || this.sinUrl || this.rolloUrl);
        
        // Obtenemos el servicio de notificaciones
        this.notification = useService("notification");
    }
    
    // Método para abrir una URL en una nueva ventana/pestaña
    openUrl(url) {
        if (!url) {
            this.notification.add(_t("URL no disponible"), { type: "warning" });
            return;
        }
        
        try {
            window.open(url, '_blank');
        } catch (error) {
            console.error("Error al abrir URL:", error);
            this.notification.add(_t("Error al abrir URL"), { type: "warning" });
        }
    }
}

// Template XML (debe ser implementado en un archivo XML separado)
/*
<?xml version="1.0" encoding="UTF-8"?>
<templates id="template" xml:space="preserve">
    <t t-name="point_of_sale.SuccessModal">
        <Dialog title="state.title" contentClass="'success-modal'">
            <div class="p-4">
                <div class="mb-4">
                    <i class="fa fa-check-circle text-success fa-3x mb-2 d-block text-center"/>
                    <h3 class="text-center" t-esc="state.message"/>
                    <p class="text-center">
                        <t t-if="state.orderName">Orden: <span t-esc="state.orderName"/></t>
                    </p>
                </div>
                
                <t t-if="hasUrls">
                    <div class="d-flex justify-content-center flex-wrap gap-2">
                        <t t-if="pdfUrl">
                            <button class="btn btn-primary" t-on-click="() => this.openUrl(pdfUrl)">
                                <i class="fa fa-file-pdf-o me-1"/> Ver PDF
                            </button>
                        </t>
                        
                        <t t-if="xmlUrl">
                            <button class="btn btn-info" t-on-click="() => this.openUrl(xmlUrl)">
                                <i class="fa fa-file-code-o me-1"/> XML
                            </button>
                        </t>
                        
                        <t t-if="sinUrl">
                            <button class="btn btn-secondary" t-on-click="() => this.openUrl(sinUrl)">
                                <i class="fa fa-barcode me-1"/> SIAT
                            </button>
                        </t>
                        
                        <t t-if="rolloUrl">
                            <button class="btn btn-success" t-on-click="() => this.openUrl(rolloUrl)">
                                <i class="fa fa-print me-1"/> Ticket
                            </button>
                        </t>
                    </div>
                </t>
                
                <div class="text-center mt-4">
                    <button class="btn btn-secondary" t-on-click="props.close">
                        Cerrar
                    </button>
                </div>
            </div>
        </Dialog>
    </t>
</templates>
*/