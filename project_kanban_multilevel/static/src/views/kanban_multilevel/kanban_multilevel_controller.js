/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanMultilevelRenderer } from "./kanban_multilevel_renderer";

export class KanbanMultilevelController extends KanbanController {
    static components = {
        ...KanbanController.components,
        KanbanRenderer: KanbanMultilevelRenderer,
    };
}
