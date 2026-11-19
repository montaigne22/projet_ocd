import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

// As common.fold: without accents, capitals, spaces nor signs (« Côte d'Ivoire »: « cotedivoire »)
const fold = (text) =>
    (text || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
const LIMIT = 8;

/**
 * « Search your country » (the home page, the page of all the countries): the countries come as
 * the person types, by their name, their English name or their code, without minding the
 * accents; the arrows choose, Enter opens the country chosen (else the first one). On the page
 * of all the countries, the list itself is filtered. Without JavaScript, the form gives the page
 * of the countries found (a single one opens its page).
 */
export class OcdCountryFind extends Interaction {
    static selector = ".o_ocd_country_find";
    dynamicContent = {
        _root: { "t-on-submit": this.onSubmit },
        ".o_ocd_country_find_input": { "t-on-input": this.onInput, "t-on-keydown": this.onKey },
    };

    setup() {
        this.inputEl = this.el.querySelector(".o_ocd_country_find_input");
        this.listEl = this.el.querySelector(".o_ocd_country_find_list");
        this.countries = JSON.parse(this.el.dataset.countries || "[]").map(([code, name, count, names]) => ({
            code,
            name,
            count,
            names: names.split(" "),
        }));
        // The page of all the countries: its list is filtered instead of a list under the field
        this.pageListEl = document.querySelector(".o_ocd_countries_list");
        this.found = [];
        this.active = -1;
    }

    start() {
        this.addListener(document, "click.noUpdate", (ev) => {
            if (!this.el.contains(ev.target)) {
                this.close();
            }
        });
    }

    /** A name that starts with what is typed first, then a name that contains it. */
    find(text) {
        const typed = fold(text);
        if (!typed) {
            return [];
        }
        const starts = this.countries.filter((country) => country.names.some((name) => name.startsWith(typed)));
        const contains = this.countries.filter(
            (country) => !starts.includes(country) && country.names.some((name) => name.includes(typed))
        );
        return [...starts, ...contains];
    }

    onInput() {
        const text = this.inputEl.value;
        if (this.pageListEl) {
            const codes = new Set(this.find(text).map((country) => country.code));
            for (const chip of this.pageListEl.children) {
                chip.hidden = Boolean(fold(text)) && !codes.has(chip.getAttribute("href").split("/").pop());
            }
            return;
        }
        this.found = this.find(text).slice(0, LIMIT);
        this.active = this.found.length ? 0 : -1;
        this.render(text);
    }

    render(text) {
        this.listEl.replaceChildren();
        if (!fold(text)) {
            this.close();
            return;
        }
        if (!this.found.length) {
            const none = document.createElement("li");
            none.className = "o_ocd_country_find_none";
            none.textContent = _t("No country with this name: try in English, or its code (CM, TG…).");
            this.listEl.appendChild(none);
        }
        this.found.forEach((country, index) => {
            const item = document.createElement("li");
            item.setAttribute("role", "presentation");
            const link = document.createElement("a");
            link.href = `/lives/${country.code}`;
            link.id = `o_ocd_country_${country.code}`;
            link.setAttribute("role", "option");
            link.setAttribute("aria-selected", index === this.active ? "true" : "false");
            const flag = document.createElement("span");
            flag.className = `o_ocd_flag o_ocd_flag_${country.code}`;
            const name = document.createElement("span");
            name.textContent = country.name;
            link.append(flag, name);
            if (country.count) {
                const count = document.createElement("b");
                count.className = "o_ocd_country_find_count";
                count.textContent = country.count;
                link.appendChild(count);
            }
            item.appendChild(link);
            this.listEl.appendChild(item);
        });
        this.listEl.hidden = false;
        this.inputEl.setAttribute("aria-expanded", "true");
        this.showActive();
    }

    showActive() {
        const links = [...this.listEl.querySelectorAll("a")];
        links.forEach((link, index) => link.setAttribute("aria-selected", index === this.active ? "true" : "false"));
        const active = links[this.active];
        if (active) {
            this.inputEl.setAttribute("aria-activedescendant", active.id);
            active.scrollIntoView({ block: "nearest" });
        } else {
            this.inputEl.removeAttribute("aria-activedescendant");
        }
    }

    close() {
        this.listEl.hidden = true;
        this.inputEl.setAttribute("aria-expanded", "false");
        this.inputEl.removeAttribute("aria-activedescendant");
    }

    onKey(ev) {
        if (ev.key === "Escape") {
            this.close();
            return;
        }
        if (this.listEl.hidden || !this.found.length) {
            return;
        }
        const moves = { ArrowDown: 1, ArrowUp: -1 };
        if (ev.key in moves) {
            ev.preventDefault();
            this.active = (this.active + moves[ev.key] + this.found.length) % this.found.length;
            this.showActive();
        }
    }

    /** Enter: the country chosen, else the first one found, at once. */
    onSubmit(ev) {
        let code = null;
        if (this.pageListEl) {
            const shown = [...this.pageListEl.children].filter((chip) => !chip.hidden);
            code = shown.length === 1 ? shown[0].getAttribute("href").split("/").pop() : null;
        } else {
            const found = this.found.length ? this.found : this.find(this.inputEl.value);
            code = (found[this.active] || found[0])?.code || null;
        }
        if (code) {
            ev.preventDefault();
            window.location.assign(`/lives/${code}`);
        }
    }
}

registry.category("public.interactions").add("ocd_live.country_find", OcdCountryFind);
