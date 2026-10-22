import {HtmlField, htmlField} from "@html_editor/fields/html_field";
import {markup, useState} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";

export class DescriptionOptimizerField extends HtmlField {
    static template = "helpdesk_mgmt_description_optimizer.DescriptionOptimizerField";

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
        return this.descriptionState.expanded ? _t("Ler menos") : _t("Ler mais");
    }

    async toggleExpanded() {
        if (this.descriptionState.expanded) {
            await this.commitChanges();
        }
        this.descriptionState.expanded = !this.descriptionState.expanded;
    }
}

export const descriptionOptimizerField = {
    ...htmlField,
    component: DescriptionOptimizerField,
};

registry.category("fields").add("description_optimizer", descriptionOptimizerField);
