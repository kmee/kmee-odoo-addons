/** @odoo-module **/

import { Component } from "@odoo/owl";
import { WipBadge } from "./wip_badge";

export class ColumnHeaders extends Component {
    static template = "project_kanban_multilevel.ColumnHeaders";
    static components = { WipBadge };
    static props = {
        stages: { type: Array },
        columns: { type: Array },
        getWipCount: { type: Function },
    };

    /**
     * Get the colspan for a parent header.
     */
    getColspan(stage) {
        return stage.has_sub_stages ? 2 : 1;
    }
}
