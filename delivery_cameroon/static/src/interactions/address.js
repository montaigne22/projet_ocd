import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { CustomerAddress } from "@portal/interactions/address";

patch(CustomerAddress.prototype, {
    /**
     * Load the districts of the chosen city, and require one when the city has districts.
     *
     * @override
     */
    async onChangeCity() {
        await super.onChangeCity(...arguments);
        if (!this.addressForm.district_id) {
            return;
        }
        const cityId = parseInt(this.addressForm.city_id.value);
        const districts = cityId
            ? await this.waitFor(rpc("/delivery_cameroon/districts", { city_id: cityId }))
            : [];
        this._setFieldChoices("district_id", districts);
        this._markRequired("district_id", districts.length > 0);
    },

    /**
     * Reset the districts when the country changes, as they belong to the previous city.
     *
     * @override
     */
    async onChangeCountry() {
        const data = await super.onChangeCountry(...arguments);
        if (this.addressForm.district_id) {
            this._setFieldChoices("district_id", []);
            this._markRequired("district_id", false);
        }
        return data;
    },
});
