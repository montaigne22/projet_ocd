import { _t } from "@web/core/l10n/translation";
import { rpc, RPCError } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

import { PaymentForm } from "@payment/interactions/payment_form";

const POLL_DELAY = 4000; // ms between two status checks
const POLL_DURATION = 5 * 60 * 1000; // ms after which the customer is sent to the status page
const FINAL_STATES = new Set(["authorized", "done", "cancel", "error"]);

patch(PaymentForm.prototype, {
    // #=== DOM MANIPULATION ===#

    /**
     * Pay Mobile Money without leaving the website: the phone number is sent to Campay, which
     * asks the customer to confirm the payment on the phone.
     *
     * @override method from @payment/interactions/payment_form
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== "campay" || paymentMethodCode !== "mobile_money" || flow === "token") {
            await super._prepareInlineForm(...arguments);
            return;
        }
        this._setPaymentFlow("direct");
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Check the phone number before creating the transaction.
     *
     * @override method from @payment/interactions/payment_form
     */
    async _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== "campay" || flow !== "direct") {
            await super._initiatePaymentFlow(...arguments);
            return;
        }
        const phoneInput = this._getCampayInlineForm()?.querySelector("[name='o_campay_phone']");
        const digits = (phoneInput?.value || "").replace(/\D/g, "").replace(/^00/, "");
        const phone = digits.length === 9 ? `237${digits}` : digits;
        if (!/^2376\d{8}$/.test(phone)) {
            this._displayErrorDialog(
                _t("Invalid number"),
                _t("Enter a Cameroonian mobile number, e.g. 6 70 00 00 00 (MTN) or 6 90 00 00 00 (Orange).")
            );
            this._enableButton();
            return;
        }
        this.campayPhone = phone;
        await super._initiatePaymentFlow(...arguments);
    },

    /**
     * Send the payment request to the phone, then wait for the confirmation.
     *
     * @override method from @payment/interactions/payment_form
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== "campay") {
            await super._processDirectFlow(...arguments);
            return;
        }
        const params = {
            reference: processingValues.reference,
            access_token: processingValues.campay_access_token,
        };
        let instructions;
        try {
            instructions = await this.waitFor(
                rpc("/payment/campay/collect", { ...params, phone: this.campayPhone })
            );
        } catch (error) {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton();
                return;
            }
            throw error;
        }
        this._showCampayWaiting(instructions);
        this._pollCampayStatus(params, Date.now() + POLL_DURATION);
    },

    /**
     * Show the confirmation instructions and unblock the page, but keep the button disabled.
     *
     * @private
     * @param {object} instructions - The USSD code and the operator returned by Campay.
     */
    _showCampayWaiting(instructions) {
        const inlineForm = this._getCampayInlineForm();
        inlineForm?.querySelector(".o_campay_phone_field")?.classList.add("d-none");
        const waiting = inlineForm?.querySelector(".o_campay_waiting");
        if (waiting) {
            const ussd = waiting.querySelector(".o_campay_ussd");
            if (ussd && instructions?.ussd_code) {
                ussd.textContent = _t(" or dial %(code)s", { code: instructions.ussd_code });
            }
            waiting.classList.remove("d-none");
        }
        this.env.bus.trigger("ui", "unblock");
    },

    /**
     * Check the payment status until it is final, then show the status page, which processes
     * it (the result of Campay is received: paid or failed).
     *
     * @private
     */
    async _pollCampayStatus(params, deadline) {
        try {
            const { state, received } = await this.waitFor(rpc("/payment/campay/status", params));
            if (received || FINAL_STATES.has(state)) {
                window.location = "/payment/status";
                return;
            }
        } catch (error) {
            if (!(error instanceof RPCError)) {
                throw error;
            }
        }
        if (Date.now() > deadline) {
            window.location = "/payment/status";
            return;
        }
        this.waitForTimeout(() => this._pollCampayStatus(params, deadline), POLL_DELAY);
    },

    /**
     * Return the inline form of the selected Campay Mobile Money option.
     *
     * @private
     * @return {HTMLElement|null}
     */
    _getCampayInlineForm() {
        const checkedRadio = this.el.querySelector("input[name='o_payment_radio']:checked");
        return checkedRadio ? this._getInlineForm(checkedRadio) : null;
    },
});
