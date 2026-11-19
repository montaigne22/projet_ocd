import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * The menu of the space of a vendor, as tabs on a phone and a tablet: the tabs scroll sideways,
 * and the page opened may be one of the last ones (« My figures », « My reviews »). Its tab is
 * brought into view, without moving the page. On a computer the menu does not scroll: nothing
 * changes.
 */
export class OcdSpaceMenu extends Interaction {
    static selector = ".o_ocd_space_menu";

    start() {
        const menu = this.el;
        const current = menu.querySelector(".o_ocd_on");
        if (!current || menu.scrollWidth <= menu.clientWidth) {
            return;
        }
        const left = current.offsetLeft - menu.offsetLeft;
        if (left + current.offsetWidth > menu.scrollLeft + menu.clientWidth) {
            menu.scrollLeft = left - (menu.clientWidth - current.offsetWidth) / 2;
        }
    }
}

registry.category("public.interactions").add("ocd_live.space_menu", OcdSpaceMenu);
