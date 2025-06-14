/** @odoo-module */
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { loadJS } from "@web/core/assets";
import { Component, useState} from "@odoo/owl";

export class PrebuiltPopup extends Component {
    static template = "pos_payment_dinger.PrebuiltPopup";
    static components = { Dialog };
    setup() {
        this.pos = usePos();
        this.order = this.props.order;
        this.line = this.props.line;
        this.uuid = this.props.uuid;
        this.paymentMethodType = this.props.paymentMethodType;
        this.paymentMethodId = this.props.paymentMethodId;
        this.token = this.props.token;
        this.countryCode="";
        const partner = this.props.order.get_partner?.() || {};
        const payment_lines = this.order.paymentlines;
        const orderlines = this.order.get_orderlines?.() || [];
        const amount_total = this.order.getTotalDue?.() || 0.00;
        const safeNumber = this.safeNumber.bind(this);

        this.state = useState({
            step: 1,
            customerName: partner.name,
            clientId:partner.id,
            email: partner.email,
            phone: partner.phone,
            address: partner.contact_address,
            billCity: partner.city,
            state: partner.state_id?.name || "Yangon",
            country: partner.country_id?.name || "Myanmar",//Here need to get the country code from dinger
            postalCode: partner.zip,
            paymentMethod: this.paymentMethodType,
            total:amount_total,
            orderLines: orderlines.map(l => ({
                product: l.product_id.display_name,
                taxes: l.tax_ids,
                discount:safeNumber(l.discount),
                price: safeNumber(l.price_unit),
                quantity: l.qty,
            })),
        });
    }

    safeNumber(val) {
        return (val === null || val === false || val === "" || (Array.isArray(val) && val.length === 0)) ? 0.00 : val;
    }

    async generateQRCode(text) {
        await loadJS("https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js");
        // Create a container div for the QR code
        const qrCodeContainerId = "dynamic_qr_code";
        const qrDiv = `o<div id="${qrCodeContainerId}" class="d-flex justify-content-center"></div>`
            let qrElement = document.getElementById(qrCodeContainerId);
            if (qrElement) {
                 const jsonString = JSON.stringify(text);
                 console.log(jsonString);
                new QRCode(qrElement, {
                    text: jsonString,  // Use token as QR data
                    width: 150,
                    height: 150
                });
            }
    }

    //Here need to create payload and silent call to diner pay method
     async nextStep() {
        if (this.state.step < 3) {
            if(this.state.step==2){
                //Initiate to get the country code
                await this.pos.data.silentCall("pos.payment", "get_country_code", [
                                            [this.paymentMethodId],
                                            this.state.country,
                                            ]).then((result) => {
                                                this.countryCode=result;
                                            }).catch((error) => {
                                                throw error;
                                           });
                //Create Payload
                const payload = {
                    providerName: this.paymentMethodType,
                    methodName: "QR",
                    totalAmount: parseFloat(this.state.total || 0.0),
                    currency: this.pos.currency?.name || "MMK",
                    orderId: this.order.name,
                    email: this.state.email || "",
                    customerPhone : this.state.phone || "",
                    customerName: this.state.customerName || "",
                    state: this.state.state || "Yangon",
                    country: this.countryCode || "MM",
                    postalCode: this.state.postalCode || "15015"
                    billAddress: this.state.address || "No Address",
                    billCity: this.state.billCity || "Yangon",
                    items: JSON.stringify(this.state.orderLines.map(line => ({
                                    name: line.product,
                                    amount: (line.price).toFixed(2),
                                    quantity: line.quantity.toString()
                    }))),
                };

                //Here initiate call to dinger with payload
                await this.pos.data.silentCall("pos.payment", "make_payment", [
                                            [this.paymentMethodId],  // Pass payment method ID
                                            this.token,
                                            payload,
                                            ]).then(async (result) => {
                                                this.state.step += 1;
                                                await this.generateQRCode(result);
                                            }).catch((error) => {
                                                throw error;
                                            });
            }
            else{
                this.state.step += 1;
            }
        }
    }

    prevStep() {
        if (this.state.step > 1) {
            this.state.step -= 1;
        }
    }
    onStepClick = (stepNumber) => {
        if (stepNumber < this.state.step) {
            this.state.step = stepNumber;
            console.log(stepNumber);
        }
    }

    //Compose payload and call dinger pay method from python
    async confirm() {
        this.props.getPayload(this.state);
        this.props.close();
    }
}
