/** @odoo-module **/

import {registry} from "@web/core/registry";
import {HtmlField} from "@web_editor/js/backend/html_field";
import {_t} from "@web/core/l10n/translation";
import {markup, useState} from "@odoo/owl";

export class DescriptionOptimizerField extends HtmlField {
    setup() {
        super.setup();
        this.descriptionState = useState({expanded: false});
    }

    get hasMore() {
        return Boolean(this.props.record.data.has_description_full);
    }

    get isCollapsed() {
        return this.hasMore && !this.descriptionState.expanded;
    }

    get markupSummary() {
        return markup(this.props.record.data.description_summary || "");
    }

    get toggleLabel() {
        return this.descriptionState.expanded ? _t("Read Less") : _t("Read More");
    }

    async toggleExpanded() {
        if (this.descriptionState.expanded) {
            await this.commitChanges();
        }
        this.descriptionState.expanded = !this.descriptionState.expanded;
    }
}

DescriptionOptimizerField.template =
    "helpdesk_mgmt_description_optimizer.DescriptionOptimizerField";
DescriptionOptimizerField.components = {...HtmlField.components};

registry.category("fields").add("description_optimizer", DescriptionOptimizerField);
