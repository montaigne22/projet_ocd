import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * A product started without network stays in the phone, its photo included, and leaves by
 * itself when the network is back (2.7 of the plan of « My products », design GererProduits).
 *
 * The drafts are kept in the database of the browser (IndexedDB), each one under the token of
 * its form: sent twice (the answer lost on a weak network), the server finds the product of the
 * first sending and adds nothing. Without this database (a private window), the form is sent as
 * before.
 */

const DB_NAME = "ocd_live";
const STORE = "product_drafts";

function openDb() {
    return new Promise((resolve, reject) => {
        if (!window.indexedDB) {
            reject(new Error("No database in this browser"));
            return;
        }
        const request = window.indexedDB.open(DB_NAME, 1);
        request.onupgradeneeded = () => {
            if (!request.result.objectStoreNames.contains(STORE)) {
                request.result.createObjectStore(STORE, { keyPath: "id" });
            }
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

async function withStore(mode, action) {
    const db = await openDb();
    try {
        return await new Promise((resolve, reject) => {
            const transaction = db.transaction(STORE, mode);
            const result = action(transaction.objectStore(STORE));
            transaction.oncomplete = () => resolve(result?.result);
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error);
        });
    } finally {
        db.close();
    }
}

export const productDrafts = {
    async all() {
        const drafts = (await withStore("readonly", (store) => store.getAll())) || [];
        return drafts.sort((a, b) => a.created - b.created);
    },
    async put(draft) {
        await withStore("readwrite", (store) => store.put(draft));
        document.dispatchEvent(new CustomEvent("ocd-drafts-changed"));
    },
    async remove(id) {
        await withStore("readwrite", (store) => store.delete(id));
        document.dispatchEvent(new CustomEvent("ocd-drafts-changed"));
    },
    /** The draft of the form of a product to add: its fields and its photo. */
    fromForm(form) {
        const data = new FormData(form);
        const photo = data.get("photo");
        return {
            id: data.get("form_token") || `${Date.now()}`,
            name: data.get("name") || "",
            price: data.get("price") || "",
            quantity: data.get("quantity") || "",
            photo: photo instanceof Blob && photo.size ? photo : null,
            photoName: photo?.name || "photo.jpg",
            created: Date.now(),
            failed: false,
        };
    },
};

/** A new token for the next product of the form (the server keeps one product per token). */
export function newFormToken() {
    const bytes = new Uint8Array(16);
    window.crypto.getRandomValues(bytes);
    return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

/**
 * « My products »: the products kept in the phone, sent as soon as the network is back (on
 * this page, when it opens or when the network comes back).
 */
export class OcdProductDrafts extends Interaction {
    static selector = ".o_ocd_my_drafts";
    dynamicContent = {
        ".o_ocd_my_draft_remove": { "t-on-click": this.onRemove },
    };

    setup() {
        this.list = this.el.querySelector(".o_ocd_my_drafts_list");
        this.template = this.el.querySelector("template");
        this.note = document.querySelector(".o_ocd_offline_note");
        this.messages = JSON.parse(this.el.dataset.messages || "{}");
        this.urls = [];
        this.sending = false;
    }

    async willStart() {
        try {
            this.drafts = await productDrafts.all();
        } catch {
            this.drafts = [];
        }
    }

    start() {
        this.render();
        this.showNetwork();
        this.addListener(window, "online", () => {
            this.showNetwork();
            this.sendAll();
        });
        this.addListener(window, "offline", () => this.showNetwork());
        this.addListener(document, "ocd-drafts-changed", () => this.refresh());
        this.sendAll();
    }

    destroy() {
        this.urls.forEach((url) => URL.revokeObjectURL(url));
    }

    showNetwork() {
        if (this.note) {
            this.note.hidden = navigator.onLine;
        }
    }

    async refresh() {
        try {
            this.drafts = await this.waitFor(productDrafts.all());
        } catch {
            return;
        }
        this.render();
    }

    render() {
        this.urls.forEach((url) => URL.revokeObjectURL(url));
        this.urls = [];
        this.list.replaceChildren();
        for (const draft of this.drafts) {
            const row = this.template.content.firstElementChild.cloneNode(true);
            row.dataset.id = draft.id;
            row.querySelector(".o_ocd_my_draft_name").textContent = draft.name;
            row.querySelector(".o_ocd_my_draft_price").textContent = `${draft.price} ${this.el.dataset.currency || ""}`.trim();
            row.querySelector(".o_ocd_my_draft_hint").textContent = draft.failed ? this.messages.failed : this.messages.hint;
            row.classList.toggle("o_ocd_my_draft_failed", !!draft.failed);
            const image = row.querySelector("img");
            if (draft.photo) {
                const url = URL.createObjectURL(draft.photo);
                this.urls.push(url);
                image.src = url;
            } else {
                image.remove();
            }
            this.list.append(row);
        }
        this.el.hidden = !this.drafts.length;
    }

    async onRemove(ev) {
        const id = ev.currentTarget.closest("[data-id]")?.dataset.id;
        if (id) {
            await this.waitFor(productDrafts.remove(id));
        }
    }

    /** Send the drafts, one after the other; the page shows the products sent. */
    async sendAll() {
        if (this.sending || !navigator.onLine || !this.drafts.some((draft) => !draft.failed)) {
            return;
        }
        this.sending = true;
        let sent = 0;
        try {
            for (const draft of this.drafts.filter((d) => !d.failed)) {
                const result = await this.waitFor(this.send(draft));
                if (result === "network" || result === "login") {
                    break; // the network is gone again, or the vendor must log in: sent later
                }
                if (result === "sent") {
                    await this.waitFor(productDrafts.remove(draft.id));
                    sent++;
                } else {
                    await this.waitFor(productDrafts.put({ ...draft, failed: true }));
                }
            }
        } finally {
            this.sending = false;
        }
        if (sent) {
            window.location.assign("/ocd/espace/moi/produits?envoye=1");
        }
    }

    async send(draft) {
        const data = new FormData();
        data.append("csrf_token", this.el.dataset.csrf);
        data.append("form_token", draft.id);
        data.append("name", draft.name);
        data.append("price", draft.price);
        if (draft.quantity !== "") {
            data.append("quantity", draft.quantity);
        }
        if (draft.photo) {
            data.append("photo", draft.photo, draft.photoName);
        }
        let response;
        try {
            response = await fetch("/ocd/espace/moi/produits", { method: "POST", body: data, credentials: "same-origin" });
        } catch {
            return "network";
        }
        // Added: « My products » after its redirection; the login page: sent once the vendor is
        // back; refused (a photo the server cannot read): the draft stays, to be added again
        if (response.status >= 500) {
            return "network";
        }
        const landed = new URL(response.url, window.location.href);
        if (landed.pathname.startsWith("/ocd/connexion")) {
            return "login";
        }
        return response.redirected && response.ok && landed.searchParams.get("envoye") === "1" ? "sent" : "refused";
    }
}

registry.category("public.interactions").add("ocd_live_shop.product_drafts", OcdProductDrafts);
