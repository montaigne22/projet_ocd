import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const REFRESH_MS = 10000;

/**
 * The live ranking: its rows are read again every 10 seconds (a page kept a few seconds in the
 * memory of the server), never while the page is hidden.
 */
export class OcdVoteRanking extends Interaction {
    static selector = ".o_ocd_vote_ranking[data-refresh]";

    start() {
        this.timer = setInterval(() => !document.hidden && this.refresh(), REFRESH_MS);
    }

    async refresh() {
        try {
            const response = await this.waitFor(fetch(this.el.dataset.refresh, { credentials: "same-origin" }));
            if (response.ok) {
                this.el.innerHTML = await this.waitFor(response.text());
            }
        } catch {
            // Network hiccup: read again later
        }
    }

    destroy() {
        clearInterval(this.timer);
    }
}

/**
 * The votes of a candidate: the button says what is paid (« Pay 900 F for 10 votes »). Without
 * JavaScript, the form works the same with « Pay ».
 */
export class OcdVoteForm extends Interaction {
    static selector = ".o_ocd_vote_form";
    dynamicContent = {
        _root: { "t-on-change": this.update, "t-on-input": this.update },
    };

    start() {
        this.update();
    }

    update() {
        const button = this.el.querySelector(".o_ocd_vote_pay");
        const chosen = this.el.querySelector("input[name='votes']:checked");
        if (!button || !chosen) {
            return;
        }
        if (chosen.value === "autre") {
            const votes = parseInt(this.el.querySelector("input[name='autre']").value) || 0;
            button.textContent = votes > 0 ? _t("Pay for %s votes", votes) : _t("Pay");
            return;
        }
        const votes = parseInt(chosen.dataset.votes);
        button.textContent = votes === 1
            ? _t("Pay %s for 1 vote", chosen.dataset.label)
            : _t("Pay %(price)s for %(votes)s votes", { price: chosen.dataset.label, votes });
    }
}

registry
    .category("public.interactions")
    .add("ocd_vote.ranking", OcdVoteRanking)
    .add("ocd_vote.form", OcdVoteForm);
