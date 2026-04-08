/** @odoo-module **/

import { Component } from "@odoo/owl";

export class WipBadge extends Component {
    static template = "project_kanban_multilevel.WipBadge";
    static props = {
        current: { type: Number },
        limit: { type: Number },
    };

    get show() {
        return this.props.limit > 0;
    }

    get label() {
        return `${this.props.current}/${this.props.limit}`;
    }

    get colorClass() {
        const { current, limit } = this.props;
        if (current > limit) {
            return "o_wip_exceeded";
        }
        if (current === limit) {
            return "o_wip_at_limit";
        }
        return "o_wip_ok";
    }
}
