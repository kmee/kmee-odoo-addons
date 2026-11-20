// Copyright 2026 KMEE
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import {
    Component,
    markup,
    onMounted,
    onWillStart,
    onWillUnmount,
    useRef,
    useState,
} from "@odoo/owl";
import {loadCSS, loadJS} from "@web/core/assets";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

const LIB = "/bpmn_process/static/lib/bpmn-js";
const CLASSES = {};
let loadingChain = Promise.resolve();
const LOCK_RENEW_MS = 5 * 60 * 1000;
const STATUS_CLASSES = ["decided", "proposal", "open"];

/**
 * Load the bpmn-js bundle of the given kind ("viewer" or "modeler").
 * Both bundles write the same global, so each class is kept as soon as its
 * script runs, one load at a time.
 */
export function loadBpmnClass(kind) {
    loadingChain = loadingChain.then(async () => {
        if (CLASSES[kind]) {
            return;
        }
        await Promise.all([
            loadCSS(`${LIB}/assets/diagram-js.css`),
            loadCSS(`${LIB}/assets/bpmn-js.css`),
            loadCSS(`${LIB}/assets/bpmn-font/css/bpmn.css`),
        ]);
        const file =
            kind === "modeler"
                ? "bpmn-modeler.production.min.js"
                : "bpmn-navigated-viewer.production.min.js";
        const previous = window.BpmnJS;
        await loadJS(`${LIB}/${file}`);
        CLASSES[kind] = window.BpmnJS;
        if (previous) {
            window.BpmnJS = previous;
        }
    });
    return loadingChain.then(() => CLASSES[kind]);
}

export class BpmnViewer extends Component {
    static template = "bpmn_process.Viewer";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.busService = useService("bus_service");
        this.canvasRef = useRef("canvas");
        const params = this.props.action.params || {};
        const context = this.props.action.context || {};
        this.processId = params.process_id || context.active_id;
        this.focusElement = params.element || null;
        this.instance = null;
        this.markers = [];
        this.lockTimer = null;
        this.state = useState({
            loading: true,
            error: "",
            data: null,
            versionId: params.version_id || null,
            compareId: params.compare_version_id || null,
            layer: "status",
            selectedId: null,
            panel: null,
            comment: "",
            editing: false,
            saving: false,
            note: "",
        });
        this.onBusNotification = this.onBusNotification.bind(this);
        onWillStart(async () => {
            if (!this.processId) {
                this.state.error = _t("Open the diagram from a process.");
                return;
            }
            await loadBpmnClass("viewer");
            await this.fetchData();
        });
        onMounted(async () => {
            this.busService.subscribe("bpmn_process/updated", this.onBusNotification);
            if (this.busService.start) {
                this.busService.start();
            }
            if (this.state.data) {
                await this.renderDiagram();
            }
        });
        onWillUnmount(() => {
            this.busService.unsubscribe("bpmn_process/updated", this.onBusNotification);
            if (this.lockTimer) {
                clearInterval(this.lockTimer);
            }
            if (this.state.editing) {
                this.orm.call("bpmn.process", "release_edit_lock", [[this.processId]]);
            }
            if (this.instance) {
                this.instance.destroy();
            }
        });
    }

    // ------------------------------------------------------------------
    // Data
    // ------------------------------------------------------------------

    get breadcrumbs() {
        return (this.env.config && this.env.config.breadcrumbs) || [];
    }

    get layers() {
        return [
            ["status", _t("Status")],
            ["tests", _t("Tests")],
            ["mine", _t("My tasks")],
            ["original", _t("Original colors")],
        ];
    }

    messageBody(message) {
        // Message bodies are sanitized HTML from mail.message.
        return markup(message.body || "");
    }

    get versionOptions() {
        return (this.state.data && this.state.data.versions) || [];
    }

    get diff() {
        return this.state.data && this.state.data.diff;
    }

    get counts() {
        const counts = {decided: 0, proposal: 0, open: 0};
        for (const element of Object.values(this.state.data.elements)) {
            if (counts[element.status] !== undefined) {
                counts[element.status]++;
            }
        }
        return counts;
    }

    async fetchData() {
        try {
            this.state.data = await this.orm.call(
                "bpmn.process",
                "get_viewer_data",
                [[this.processId]],
                {
                    version_id: this.state.versionId || false,
                    compare_version_id: this.state.compareId || false,
                }
            );
            this.state.error = this.state.data.xml
                ? ""
                : _t("This process has no diagram yet: import a BPMN file.");
        } catch (error) {
            this.state.error = (error.data && error.data.message) || String(error);
            this.state.data = null;
        } finally {
            this.state.loading = false;
        }
    }

    async refresh(rerender = true) {
        const previous = this.state.data && this.state.data.version;
        await this.fetchData();
        const current = this.state.data && this.state.data.version;
        if (!this.state.data || this.state.error) {
            return;
        }
        if (rerender || !previous || !current || previous.id !== current.id) {
            await this.renderDiagram();
        } else {
            this.applyLayer();
        }
        if (this.state.selectedId) {
            await this.loadPanel(this.state.selectedId);
        }
    }

    async onBusNotification(payload) {
        if (!payload || payload.process_id !== this.processId || this.state.editing) {
            return;
        }
        if (payload.kind === "version") {
            if (!this.state.data.version || this.state.data.version.is_current) {
                this.state.versionId = null;
            }
            await this.refresh(true);
        } else {
            await this.refresh(false);
        }
    }

    // ------------------------------------------------------------------
    // Diagram
    // ------------------------------------------------------------------

    async renderDiagram(kind = "viewer") {
        const el = this.canvasRef.el;
        if (!el || !this.state.data || !this.state.data.xml) {
            return;
        }
        if (this.instance) {
            this.instance.destroy();
            this.instance = null;
        }
        this.markers = [];
        const BpmnClass = await loadBpmnClass(kind);
        const options = {container: el};
        if (kind === "modeler") {
            options.keyboard = {bindTo: document};
        }
        this.instance = new BpmnClass(options);
        try {
            const result = await this.instance.importXML(this.state.data.xml);
            if (result.warnings && result.warnings.length) {
                console.warn("bpmn_process: import warnings", result.warnings);
            }
        } catch (error) {
            this.state.error = _t("The diagram could not be drawn: %s", error.message);
            return;
        }
        const canvas = this.instance.get("canvas");
        canvas.zoom("fit-viewport", "auto");
        if (kind === "viewer") {
            this.instance.get("eventBus").on("element.click", (event) => {
                this.select(event.element.id);
            });
        }
        this.applyLayer();
        if (this.focusElement) {
            const target = this.instance.get("elementRegistry").get(this.focusElement);
            if (target) {
                canvas.scrollToElement(target, {
                    top: 200,
                    bottom: 200,
                    left: 300,
                    right: 300,
                });
                await this.select(this.focusElement);
            }
            this.focusElement = null;
        }
    }

    addMarker(id, cls) {
        const registryService = this.instance.get("elementRegistry");
        if (!registryService.get(id)) {
            return;
        }
        this.instance.get("canvas").addMarker(id, cls);
        this.markers.push([id, cls]);
    }

    /**
     * Marker class of an element in the current layer, or null.
     *
     * @param {Object} element data of the element from the server
     * @returns {String|null}
     */
    layerClass(element) {
        const layer = this.state.layer;
        if (layer === "status") {
            return STATUS_CLASSES.includes(element.status)
                ? `o_bpmn_st_${element.status}`
                : null;
        }
        if (layer === "tests") {
            return element.test_state === "none"
                ? "o_bpmn_dim"
                : `o_bpmn_test_${element.test_state}`;
        }
        if (layer === "mine") {
            return element.mine ? "o_bpmn_mine" : "o_bpmn_dim";
        }
        return null;
    }

    markDiff(diff) {
        const groups = [
            [diff.added, "o_bpmn_diff_added"],
            [Object.keys(diff.changed), "o_bpmn_diff_changed"],
            [diff.moved, "o_bpmn_diff_moved"],
        ];
        for (const [ids, cls] of groups) {
            for (const id of ids) {
                this.addMarker(id, cls);
            }
        }
    }

    drawBadges(elements) {
        const overlays = this.instance.get("overlays");
        overlays.remove({type: "o_bpmn_badge"});
        const registryService = this.instance.get("elementRegistry");
        for (const [id, element] of Object.entries(elements)) {
            if (!element.messages || !registryService.get(id)) {
                continue;
            }
            const badge = document.createElement("div");
            badge.className = "o_bpmn_badge";
            badge.title = _t("Comments");
            badge.textContent = String(element.messages);
            overlays.add(id, "o_bpmn_badge", {
                position: {top: -10, right: 10},
                html: badge,
            });
        }
    }

    applyLayer() {
        if (!this.instance || this.state.editing) {
            return;
        }
        const canvas = this.instance.get("canvas");
        for (const [id, cls] of this.markers) {
            canvas.removeMarker(id, cls);
        }
        this.markers = [];
        const elements = this.state.data.elements;
        if (this.diff) {
            this.markDiff(this.diff);
        } else {
            for (const [id, element] of Object.entries(elements)) {
                const cls = this.layerClass(element);
                if (cls) {
                    this.addMarker(id, cls);
                }
            }
        }
        if (this.state.selectedId) {
            this.addMarker(this.state.selectedId, "o_bpmn_selected");
        }
        this.drawBadges(elements);
    }

    setLayer(layer) {
        this.state.layer = layer;
        this.applyLayer();
    }

    fit() {
        if (this.instance) {
            this.instance.get("canvas").zoom("fit-viewport", "auto");
        }
    }

    // ------------------------------------------------------------------
    // Panel
    // ------------------------------------------------------------------

    async select(id) {
        this.state.selectedId = id;
        this.state.comment = "";
        this.applyLayer();
        await this.loadPanel(id);
    }

    async loadPanel(id) {
        const record = this.state.data.elements[id];
        if (record) {
            this.state.panel = await this.orm.call("bpmn.element", "get_panel_data", [
                [record.id],
            ]);
            return;
        }
        const shape = this.instance && this.instance.get("elementRegistry").get(id);
        const bo = shape && shape.businessObject;
        this.state.panel = bo
            ? {
                  id: false,
                  bpmn_id: id,
                  name: bo.name || id,
                  element_type: (bo.$type || "").replace("bpmn:", ""),
              }
            : null;
    }

    closePanel() {
        this.state.selectedId = null;
        this.state.panel = null;
        this.applyLayer();
    }

    async setStatus(ev) {
        const panel = this.state.panel;
        await this.orm.write("bpmn.element", [panel.id], {
            status: ev.target.value || false,
        });
        await this.refresh(false);
    }

    async postComment() {
        const body = this.state.comment.trim();
        if (!body || !this.state.panel || !this.state.panel.id) {
            return;
        }
        await this.orm.call("bpmn.element", "post_comment", [
            [this.state.panel.id],
            body,
        ]);
        this.state.comment = "";
        await this.refresh(false);
    }

    openInOdoo() {
        const action = this.state.panel && this.state.panel.open_action;
        if (action) {
            this.actionService.doAction(action);
        }
    }

    openRecord() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "bpmn.element",
            res_id: this.state.panel.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    statusLabel(status) {
        return (
            {
                decided: _t("Decided"),
                proposal: _t("Proposal"),
                open: _t("Open"),
            }[status] || ""
        );
    }

    diffName(id) {
        return (this.diff && this.diff.names && this.diff.names[id]) || id;
    }

    // ------------------------------------------------------------------
    // Versions
    // ------------------------------------------------------------------

    async onVersionChange(ev) {
        this.state.versionId = parseInt(ev.target.value, 10) || null;
        await this.refresh(true);
    }

    async onCompareChange(ev) {
        this.state.compareId = parseInt(ev.target.value, 10) || null;
        await this.refresh(true);
    }

    async clearCompare() {
        this.state.compareId = null;
        await this.refresh(true);
    }

    download() {
        const version = this.state.data.version;
        const url = version.is_current
            ? `/bpmn_process/export/${this.processId}`
            : `/bpmn_process/version/${version.id}`;
        this.actionService.doAction({
            type: "ir.actions.act_url",
            url,
            target: "download",
        });
    }

    // ------------------------------------------------------------------
    // Editor with lock
    // ------------------------------------------------------------------

    async startEdit() {
        const result = await this.orm.call("bpmn.process", "acquire_edit_lock", [
            [this.processId],
        ]);
        if (!result.ok) {
            this.notification.add(_t("Being edited by %s.", result.user), {
                type: "warning",
            });
            await this.refresh(false);
            return;
        }
        this.state.versionId = null;
        this.state.compareId = null;
        await this.fetchData();
        this.closePanel();
        this.state.editing = true;
        this.state.note = "";
        await this.renderDiagram("modeler");
        this.lockTimer = setInterval(() => {
            this.orm.call("bpmn.process", "acquire_edit_lock", [[this.processId]]);
        }, LOCK_RENEW_MS);
    }

    async stopEditing() {
        if (this.lockTimer) {
            clearInterval(this.lockTimer);
            this.lockTimer = null;
        }
        this.state.editing = false;
        await this.refresh(true);
    }

    async saveEdit() {
        this.state.saving = true;
        try {
            const {xml} = await this.instance.saveXML({format: true});
            const result = await this.orm.call("bpmn.process", "save_edited_xml", [
                [this.processId],
                xml,
                this.state.note || "",
            ]);
            this.notification.add(_t("Saved as version %s.", result.version), {
                type: "success",
            });
            await this.stopEditing();
        } finally {
            this.state.saving = false;
        }
    }

    async cancelEdit() {
        await this.orm.call("bpmn.process", "release_edit_lock", [[this.processId]]);
        await this.stopEditing();
    }
}

registry.category("actions").add("bpmn_process.viewer", BpmnViewer);
