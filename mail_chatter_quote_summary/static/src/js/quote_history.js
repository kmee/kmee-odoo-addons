/** @odoo-module **/
/*
 * Lazy-loads the quoted email history of a chatter message.
 *
 * The server (mail.message._message_format) renders only the most recent reply
 * plus a ".o_quote_history" toggle. A single delegated click listener fetches
 * the full history on demand via RPC. It never mutates the DOM during render,
 * so it does not race with the OWL message render cycle.
 */
odoo.define("mail_chatter_quote_summary.quote_history", function (require) {
    "use strict";

    const core = require("web.core");
    const rpc = require("web.rpc");
    const _t = core._t;

    const CHUNK_SIZE = 25;

    async function _loadHistory(messageId) {
        let offset = 0;
        let html = "";
        while (offset !== false) {
            const result = await rpc.query({
                model: "mail.message",
                method: "load_quote_history_chunk",
                args: [[messageId], offset, CHUNK_SIZE],
            });
            html += result.html || "";
            offset = result.next_offset;
        }
        return html;
    }

    async function _onToggle(button) {
        const wrapper = button.closest(".o_quote_history");
        if (!wrapper || wrapper.dataset.loading === "1") {
            return;
        }
        const messageId = parseInt(wrapper.dataset.mailMessageId, 10);
        if (!messageId) {
            return;
        }

        let content = wrapper.querySelector(".o_quote_history_content");
        if (content) {
            const hidden = content.style.display === "none";
            content.style.display = hidden ? "" : "none";
            button.textContent = hidden ? _t("Ler menos") : _t("Ler mais");
            return;
        }

        wrapper.dataset.loading = "1";
        try {
            const html = await _loadHistory(messageId);
            content = document.createElement("div");
            content.className = "o_quote_history_content";
            content.innerHTML = html;
            wrapper.insertBefore(content, button);
            button.textContent = _t("Ler menos");
        } finally {
            delete wrapper.dataset.loading;
        }
    }

    document.addEventListener("click", function (ev) {
        const button = ev.target.closest(".o_quote_history_btn");
        if (!button) {
            return;
        }
        ev.preventDefault();
        _onToggle(button);
    });
});
