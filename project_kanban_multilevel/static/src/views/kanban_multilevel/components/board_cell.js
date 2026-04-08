/** @odoo-module **/

import { Component } from "@odoo/owl";
import { CompactCard } from "./compact_card";

export class BoardCell extends Component {
    static template = "project_kanban_multilevel.BoardCell";
    static components = { CompactCard };
    static props = {
        tasks: { type: Array },
        stageId: { type: Number },
        subStage: { type: [String, { value: null }] },
        swimlaneId: { type: [Number, { value: false }] },
        swimlaneColor: { type: String, optional: true },
        isExpedite: { type: Boolean, optional: true },
        onCardDrop: { type: Function, optional: true },
        onCardClick: { type: Function, optional: true },
    };

    get cellClasses() {
        const cls = ["o_board_cell"];
        if (this.props.isExpedite) {
            cls.push("o_cell_expedite");
        }
        return cls.join(" ");
    }

    onDragOver(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
        ev.currentTarget.classList.add("o_cell_drag_over");
    }

    onDragLeave(ev) {
        ev.currentTarget.classList.remove("o_cell_drag_over");
    }

    onDrop(ev) {
        ev.preventDefault();
        ev.currentTarget.classList.remove("o_cell_drag_over");
        try {
            const payload = JSON.parse(ev.dataTransfer.getData("text/plain"));
            if (payload.taskId && this.props.onCardDrop) {
                this.props.onCardDrop(payload.taskId, {
                    stageId: this.props.stageId,
                    subStage: this.props.subStage,
                    swimlaneId: this.props.swimlaneId,
                });
            }
        } catch {
            // ignore invalid drag data
        }
    }
}
