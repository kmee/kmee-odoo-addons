/** @odoo-module **/

import { Component } from "@odoo/owl";

export class CompactCard extends Component {
    static template = "project_kanban_multilevel.CompactCard";
    static props = {
        record: { type: Object },
        color: { type: String, optional: true },
        onCardClick: { type: Function, optional: true },
    };

    get data() {
        return this.props.record.data || this.props.record;
    }

    get taskId() {
        return this.data.id || this.props.record.resId;
    }

    get taskName() {
        const d = this.data;
        return d.name || d.display_name || "";
    }

    get cardSize() {
        return this.data.card_size || 1;
    }

    get isBlocked() {
        return this.data.is_blocked || false;
    }

    get agingDays() {
        return this.data.aging_days || 0;
    }

    get showAging() {
        return this.agingDays > 5;
    }

    get assigneeAvatar() {
        const data = this.data;
        // Odoo 18: user_ids can be array of ids, or a recordList proxy
        let userId = data.user_ids;
        if (!userId) return null;
        // If it's a records proxy with .records
        if (userId.records && userId.records.length > 0) {
            return `/web/image/res.users/${userId.records[0].resId}/avatar_128`;
        }
        // Plain array
        if (Array.isArray(userId) && userId.length > 0) {
            const id = Array.isArray(userId[0]) ? userId[0][0] : userId[0];
            return `/web/image/res.users/${id}/avatar_128`;
        }
        return null;
    }

    get sidebarColor() {
        return this.props.color || "#714B67";
    }

    get cardClasses() {
        const cls = ["o_compact_card"];
        if (this.isBlocked) {
            cls.push("o_compact_card_blocked");
        }
        if (this.showAging) {
            cls.push("o_compact_card_aging");
        }
        return cls.join(" ");
    }

    get priority() {
        const p = this.data.priority;
        return p === "1" || p === 1;
    }

    onDragStart(ev) {
        const id = this.taskId;
        ev.dataTransfer.setData(
            "text/plain",
            JSON.stringify({ taskId: id })
        );
        ev.dataTransfer.effectAllowed = "move";
    }

    onClick() {
        if (this.props.onCardClick) {
            this.props.onCardClick(this.taskId);
        }
    }
}
