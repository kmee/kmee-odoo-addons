/** @odoo-module **/

import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("helpdesk_mgmt_description_optimizer_tour", {
    test: true,
    steps: () => [
        {
            content: "The long description starts collapsed on its summary",
            trigger: ".o_field_description_optimizer .o_description_optimizer_summary",
            isCheck: true,
        },
        {
            content: "Expand the full description",
            trigger:
                ".o_field_description_optimizer button.o_description_optimizer_toggle",
            run: "click",
        },
        {
            content: "The full description is shown in the editor",
            trigger:
                ".o_field_description_optimizer .odoo-editor-editable:contains('Linha 119')",
            isCheck: true,
        },
        {
            content: "Collapse it again",
            trigger:
                ".o_field_description_optimizer button.o_description_optimizer_toggle",
            run: "click",
        },
        {
            content: "Back to the summary",
            trigger: ".o_field_description_optimizer .o_description_optimizer_summary",
            isCheck: true,
        },
    ],
});
