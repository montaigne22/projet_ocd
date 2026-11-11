import { _t } from "@web/core/l10n/translation";
import {
    ClientErrorDialog,
    ErrorDialog,
    NetworkErrorDialog,
    odooExceptionTitleMap,
    RPCErrorDialog,
} from "@web/core/errors/error_dialogs";
import { patch } from "@web/core/utils/patch";

// The error windows of the web client, without the name of Odoo
ErrorDialog.title = _t("Error");
ClientErrorDialog.title = _t("Error in the page");
NetworkErrorDialog.title = _t("Connection lost");

patch(RPCErrorDialog.prototype, {
    inferTitle() {
        super.inferTitle();
        if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
            return;
        }
        const titles = {
            server: _t("Server error"),
            script: _t("Error in the page"),
            network: _t("Connection lost"),
        };
        if (titles[this.props.type]) {
            this.title = titles[this.props.type];
        }
    },
});
