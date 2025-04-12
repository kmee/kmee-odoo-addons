/** @odoo-module **/
import {WebClient} from "@web/webclient/webclient";
import {patch} from "web.utils";

patch(WebClient.prototype, "remove_odoo_word.WebClient", {
    setup() {
        this._super();
        this.title.setParts({zopenerp: ""});
    },
});
