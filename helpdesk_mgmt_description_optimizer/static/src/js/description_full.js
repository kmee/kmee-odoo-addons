/** @odoo-module **/
/*
 * Lazy-loads the full helpdesk ticket description on the form view.
 *
 * The server stores a summary in `description` and the full content in
 * `description_full`. When `has_description_full` is set, a "Ler mais" toggle is
 * injected; the full content is fetched on demand via the generic
 * `load_optimizer_full_chunk` RPC. No polling (no setInterval); reacts to the
 * form load / hash change. Integration point for Odoo 16 — validate in env.
 */
odoo.define("helpdesk_mgmt_description_optimizer.description_full", function (require) {
    "use strict";

    const core = require("web.core");
    const rpc = require("web.rpc");
    const _t = core._t;

    const MODEL = "helpdesk.ticket";
    const CHUNK_SIZE = 25;
    const CONTAINER_SELECTORS = [
        '.o_form_view .o_field_html[name="description"] .note-editable',
        '.o_form_view .o_field_html[name="description"]',
    ];

    function _currentTicketId() {
        const params = new URLSearchParams(
            decodeURIComponent(window.location.hash || "").replace(/^#/, "")
        );
        if (params.get("model") && params.get("model") !== MODEL) {
            return null;
        }
        const id = parseInt(params.get("id"), 10);
        return Number.isNaN(id) ? null : id;
    }

    function _container() {
        for (const selector of CONTAINER_SELECTORS) {
            const el = document.querySelector(selector);
            if (el) {
                return el;
            }
        }
        return null;
    }

    async function _loadFull(ticketId) {
        let offset = 0;
        let html = "";
        while (offset !== false) {
            const result = await rpc.query({
                model: MODEL,
                method: "load_optimizer_full_chunk",
                args: [[ticketId], "description_full", offset, CHUNK_SIZE],
            });
            html += result.html || "";
            offset = result.next_offset;
        }
        return html;
    }

    function _buildToggle(container, ticketId) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn btn-link o_description_full_btn";
        button.textContent = _t("Ler mais");
        button.dataset.expanded = "0";
        const summary = container.innerHTML;

        button.addEventListener("click", async () => {
            if (button.dataset.loading === "1") {
                return;
            }
            if (button.dataset.expanded === "1") {
                container.innerHTML = summary;
                button.dataset.expanded = "0";
                button.textContent = _t("Ler mais");
                return;
            }
            button.dataset.loading = "1";
            try {
                container.innerHTML = await _loadFull(ticketId);
                button.dataset.expanded = "1";
                button.textContent = _t("Ler menos");
            } finally {
                delete button.dataset.loading;
            }
        });
        container.parentNode.insertBefore(button, container.nextSibling);
    }

    async function _init() {
        const ticketId = _currentTicketId();
        if (!ticketId) {
            return;
        }
        const container = _container();
        if (!container || container.dataset.descriptionFullReady === "1") {
            return;
        }
        const [record] = await rpc.query({
            model: MODEL,
            method: "read",
            args: [[ticketId], ["has_description_full"]],
        });
        container.dataset.descriptionFullReady = "1";
        if (record && record.has_description_full) {
            _buildToggle(container, ticketId);
        }
    }

    function _schedule() {
        window.setTimeout(
            () =>
                _init().catch(() => {
                    // Ignore: form not ready or RPC failed.
                }),
            200
        );
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", _schedule, {once: true});
    } else {
        _schedule();
    }
    window.addEventListener("hashchange", _schedule);
});
