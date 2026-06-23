/** @odoo-module **/

import core from "web.core";
import rpc from "web.rpc";

const _t = core._t;
const MODEL = "helpdesk.ticket";
const CHUNK_SIZE = 25;
const READY_ATTR = "descriptionFullReady";
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

async function _scan() {
    const ticketId = _currentTicketId();
    if (!ticketId) {
        return;
    }
    const container = _container();
    if (!container || container.dataset[READY_ATTR] === "1") {
        return;
    }
    container.dataset[READY_ATTR] = "1";
    let record;
    try {
        [record] = await rpc.query({
            model: MODEL,
            method: "read",
            args: [[ticketId], ["has_description_full"]],
        });
    } catch (err) {
        delete container.dataset[READY_ATTR];
        return;
    }
    if (!container.isConnected) {
        return;
    }
    if (record && record.has_description_full) {
        _buildToggle(container, ticketId);
    }
}

let scheduled = false;
function _schedule() {
    if (scheduled) {
        return;
    }
    scheduled = true;
    window.requestAnimationFrame(() => {
        scheduled = false;
        _scan().catch(() => {});
    });
}

function _start() {
    _schedule();
    new MutationObserver(_schedule).observe(document.body, {
        childList: true,
        subtree: true,
    });
    window.addEventListener("hashchange", _schedule);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _start, {once: true});
} else {
    _start();
}
