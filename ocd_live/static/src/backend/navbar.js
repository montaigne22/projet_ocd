import { patch } from "@web/core/utils/patch";
import { useListener } from "@odoo/owl";
import { NavBar } from "@web/webclient/navbar/navbar";
import { render } from "@web/owl2/utils";

const OCD_APP = "ocd_live.ocd_live_menu_root";

/**
 * Back office of OCD Live, as in the validated design: the menus of the app are links in the
 * dark bar, and the menus of the current section are tabs in a white bar below it.
 */
patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        useListener(this.env.bus, "ACTION_MANAGER:UI-UPDATED", () => render(this));
    },

    get isOcdApp() {
        return this.currentApp?.xmlid === OCD_APP;
    },

    ocdFirstLeaf(menu) {
        if (menu.actionID || !menu.childrenTree?.length) {
            return menu;
        }
        return this.ocdFirstLeaf(menu.childrenTree[0]);
    },

    ocdLeaves(menu) {
        if (!menu.childrenTree?.length) {
            return [menu];
        }
        return menu.childrenTree.flatMap((child) => this.ocdLeaves(child));
    },

    /** Id of the action shown (currentAction of the action service is asynchronous). */
    get ocdActionId() {
        return this.actionService.currentController?.action?.id || null;
    },

    /**
     * Section of the action shown. An action without menu (a list opened from the dashboard,
     * another view of the bookings…) keeps the section and the tab shown before it.
     */
    get ocdCurrentSection() {
        const actionId = this.ocdActionId;
        const found =
            actionId &&
            this.currentAppSections.find((section) =>
                this.ocdLeaves(section).some((menu) => menu.actionID === actionId)
            );
        if (found) {
            this._ocdSectionId = found.id;
            return found;
        }
        return this.currentAppSections.find((section) => section.id === this._ocdSectionId) || null;
    },

    get ocdCurrentMenu() {
        const actionId = this.ocdActionId;
        const section = this.ocdCurrentSection;
        if (!section) {
            return null;
        }
        const leaves = this.ocdLeaves(section);
        const found = leaves.find((menu) => menu.actionID === actionId);
        if (found) {
            this._ocdMenuId = found.id;
            return found;
        }
        return leaves.find((menu) => menu.id === this._ocdMenuId) || null;
    },

    get ocdSubMenus() {
        const section = this.ocdCurrentSection;
        return section && section.childrenTree?.length ? this.ocdLeaves(section) : [];
    },
});
