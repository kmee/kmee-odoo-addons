/** @odoo-module **/

import { Component } from "@odoo/owl";

export class InitiativesLane extends Component {
    static template = "project_kanban_multilevel.InitiativesLane";
    static props = {
        initiatives: { type: Array },
        stages: { type: Array },
        columns: { type: Array },
        collapsed: { type: Boolean },
        onToggle: { type: Function, optional: true },
    };

    get initiativesByStage() {
        const map = {};
        for (const stage of this.props.stages) {
            map[stage.id] = [];
        }
        for (const init of this.props.initiatives) {
            const stageId = init.stage_id
                ? init.stage_id[0] || init.stage_id
                : null;
            if (stageId && map[stageId]) {
                map[stageId].push(init);
            }
        }
        return map;
    }

    getProgressSquares(initiative) {
        try {
            return JSON.parse(initiative.child_progress_data || "[]");
        } catch {
            return [];
        }
    }

    getAreaColor(areaType) {
        switch (areaType) {
            case "done":
                return "#16a34a";
            case "progress":
                return "#2563eb";
            case "requested":
                return "#9ca3af";
            default:
                return "#9ca3af";
        }
    }

    toggle() {
        if (this.props.onToggle) {
            this.props.onToggle();
        }
    }
}
