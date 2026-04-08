/** @odoo-module **/

import { Component } from "@odoo/owl";
import { BoardCell } from "./board_cell";

export class SwimlaneBand extends Component {
    static template = "project_kanban_multilevel.SwimlaneBand";
    static components = { BoardCell };
    static props = {
        swimlane: { type: [Object, { value: null }] },
        columns: { type: Array },
        getTasksForCell: { type: Function },
        collapsed: { type: Boolean },
        onToggle: { type: Function, optional: true },
        onCardDrop: { type: Function, optional: true },
        onCardClick: { type: Function, optional: true },
    };

    get swimlaneId() {
        return this.props.swimlane ? this.props.swimlane.id : false;
    }

    get label() {
        if (!this.props.swimlane) {
            return "Sem categoria";
        }
        return this.props.swimlane.name;
    }

    get icon() {
        return this.props.swimlane?.icon || "◆";
    }

    get isExpedite() {
        return this.props.swimlane?.is_expedite || false;
    }

    get swimlaneColor() {
        return this.props.swimlane ? this.props.swimlane.color : "#9ca3af";
    }

    get labelClasses() {
        const cls = ["o_swimlane_label"];
        if (this.isExpedite) {
            cls.push("o_label_expedite");
        }
        return cls.join(" ");
    }

    getCollapsedCount(col) {
        const tasks = this.props.getTasksForCell(
            this.swimlaneId,
            col.stageId,
            col.subStage
        );
        return tasks.length;
    }

    getCellClasses(col) {
        // Add expedite class directly on cell since parent has display:contents
        if (this.isExpedite) {
            return "o_board_cell o_cell_expedite";
        }
        return "o_board_cell";
    }

    toggle() {
        if (this.props.onToggle) {
            this.props.onToggle(this.swimlaneId);
        }
    }
}
