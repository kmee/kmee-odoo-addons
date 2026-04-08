/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";
import { KanbanMultilevelController } from "./kanban_multilevel_controller";
import { KanbanMultilevelRenderer } from "./kanban_multilevel_renderer";

export class KanbanMultilevelArchParser extends KanbanArchParser {}

export const kanbanMultilevelView = {
    ...kanbanView,
    type: "kanban_multilevel",
    display_name: "Kanban Multilevel",
    Controller: KanbanMultilevelController,
    Renderer: KanbanMultilevelRenderer,
    ArchParser: KanbanMultilevelArchParser,
};

registry.category("views").add("kanban_multilevel", kanbanMultilevelView);
