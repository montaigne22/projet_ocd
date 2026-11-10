import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const POLL_DELAY = 5000;

/**
 * A page waiting for an answer (a payment in progress, a live link checked by the team) asks
 * for its state now and then, and reloads once the state has changed.
 */
export class OcdLivePoll extends Interaction {
    static selector = ".o_ocd_poll[data-poll-url]";

    start() {
        this.state = this.el.dataset.state;
        this.waitForTimeout(() => this.poll(), POLL_DELAY);
    }

    async poll() {
        let state = this.state;
        const params = this.el.dataset.accessToken ? { access_token: this.el.dataset.accessToken } : {};
        try {
            ({ state } = await this.waitFor(rpc(this.el.dataset.pollUrl, params)));
        } catch {
            // Network hiccup: ask again later
        }
        if (state !== this.state) {
            window.location.reload();
            return;
        }
        this.waitForTimeout(() => this.poll(), POLL_DELAY);
    }
}

registry.category("public.interactions").add("ocd_live.poll", OcdLivePoll);
