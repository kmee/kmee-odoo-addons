/** @odoo-module **/

import { Component, useState, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DetailPanel extends Component {
    static template = "project_kanban_multilevel.DetailPanel";
    static props = {
        taskId: { type: [Number, { value: null }] },
        onClose: { type: Function },
        onOpenForm: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            task: null,
            subtasks: [],
            loading: false,
        });
        if (this.props.taskId) {
            this._loadTask(this.props.taskId);
        }
        onWillUpdateProps((nextProps) => {
            if (nextProps.taskId && nextProps.taskId !== this.props.taskId) {
                this._loadTask(nextProps.taskId);
            }
        });
    }

    async _loadTask(taskId) {
        this.state.loading = true;
        try {
            const [tasks, subtasks] = await Promise.all([
                this.orm.read("project.task", [taskId], [
                    "name",
                    "display_name",
                    "stage_id",
                    "user_ids",
                    "priority",
                    "swimlane_id",
                    "sub_stage",
                    "card_size",
                    "is_blocked",
                    "blocked_reason",
                    "aging_days",
                    "is_initiative",
                    "tag_ids",
                    "date_deadline",
                    "description",
                ]),
                this.orm.searchRead(
                    "project.task",
                    [["parent_id", "=", taskId]],
                    ["name", "stage_id", "user_ids"],
                    { order: "sequence, id" }
                ),
            ]);
            this.state.task = tasks[0] || null;
            this.state.subtasks = subtasks;
        } catch {
            this.state.task = null;
            this.state.subtasks = [];
        }
        this.state.loading = false;
    }

    get task() {
        return this.state.task;
    }

    get subtasks() {
        return this.state.subtasks;
    }

    get stageName() {
        const s = this.task?.stage_id;
        if (!s) return "";
        return Array.isArray(s) ? s[1] : s;
    }

    get swimlaneName() {
        const s = this.task?.swimlane_id;
        if (!s) return "Sem categoria";
        return Array.isArray(s) ? s[1] : s;
    }

    get priorityLabel() {
        const p = this.task?.priority;
        if (p === "1" || p === 1) return "Alta";
        if (p === "2" || p === 2) return "Urgente";
        return "Normal";
    }

    get subStageLabel() {
        const ss = this.task?.sub_stage;
        return ss === "done" ? "Feito" : "Fazendo";
    }

    get avatarUrl() {
        const userIds = this.task?.user_ids;
        if (!userIds || !userIds.length) return null;
        const id = Array.isArray(userIds[0]) ? userIds[0][0] : userIds[0];
        return `/web/image/res.users/${id}/avatar_128`;
    }

    isSubtaskDone(subtask) {
        const stage = subtask.stage_id;
        if (!stage) return false;
        const name = Array.isArray(stage) ? stage[1] : "";
        return name.toLowerCase().includes("conclu") || name.toLowerCase().includes("done");
    }

    onClose() {
        this.props.onClose();
    }

    onOpenForm() {
        this.props.onOpenForm(this.props.taskId);
    }
}
