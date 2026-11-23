// Copyright 2026 KMEE
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("bpmn_process_viewer_tour", {
    steps: () => [
        {
            content: "Open the diagram",
            trigger: "button[name=action_open_viewer]",
            run: "click",
        },
        {
            content: "The diagram is drawn with the status colors",
            trigger:
                ".o_bpmn_canvas .djs-element.o_bpmn_st_decided[data-element-id='Task_Sample_Quote']",
        },
        {
            content: "Select a task",
            trigger: ".o_bpmn_canvas .djs-element[data-element-id='Task_Sample_Quote']",
            run: "click",
        },
        {
            content: "The panel shows the task",
            trigger: ".o_bpmn_panel h4:contains('Send quotation')",
        },
        {
            content: "Write a comment",
            trigger: ".o_bpmn_panel textarea",
            run: "edit Comment from the tour",
        },
        {
            content: "Post it",
            trigger: ".o_bpmn_panel button.o_bpmn_post:enabled",
            run: "click",
        },
        {
            content: "The comment is listed",
            trigger: ".o_bpmn_panel .o_bpmn_message:contains('Comment from the tour')",
        },
        {
            content: "The task shows a comment badge",
            trigger: ".o_bpmn_canvas .o_bpmn_badge:contains('1')",
        },
        {
            content: "Show the test layer",
            trigger: ".o_bpmn_layer[data-layer=tests]",
            run: "click",
        },
        {
            content: "The failed test is red",
            trigger:
                ".o_bpmn_canvas .djs-element.o_bpmn_test_failed[data-element-id='Task_Sample_Invoice']",
        },
        {
            content: "Start editing",
            trigger: ".o_bpmn_edit",
            run: "click",
        },
        {
            content: "The modeler palette is there",
            trigger: ".o_bpmn_canvas .djs-palette",
        },
        {
            content: "Save without changes",
            trigger: ".o_bpmn_save",
            run: "click",
        },
        {
            content: "Back to the viewer",
            trigger: ".o_bpmn_edit",
        },
    ],
});
