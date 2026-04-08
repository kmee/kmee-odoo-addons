/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { CompactCard } from "./components/compact_card";
import { BoardCell } from "./components/board_cell";
import { SwimlaneBand } from "./components/swimlane_band";
import { ColumnHeaders } from "./components/column_headers";
import { InitiativesLane } from "./components/initiatives_lane";
import { WipBadge } from "./components/wip_badge";
import { DetailPanel } from "./components/detail_panel";

export class KanbanMultilevelRenderer extends KanbanRenderer {
    static template = "project_kanban_multilevel.KanbanMultilevelRenderer";
    static components = {
        ...KanbanRenderer.components,
        CompactCard,
        BoardCell,
        SwimlaneBand,
        ColumnHeaders,
        InitiativesLane,
        WipBadge,
        DetailPanel,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.multilevel = useState({
            enabled: false,
            swimlanes: [],
            stages: [],
            initiatives: [],
            projectData: {},
            loaded: false,
        });

        this.uiState = useState({
            collapsedSwimlanes: {},
            collapsedInitiatives: false,
            selectedTaskId: null,
            searchText: "",
            filterSwimlaneId: null,
            filterUserId: null,
        });

        // Bind methods for passing to child components
        this.onCardDrop = this.onCardDrop.bind(this);
        this.onCardClick = this.onCardClick.bind(this);
        this.onClosePanel = this.onClosePanel.bind(this);
        this.onOpenForm = this.onOpenForm.bind(this);
        this.onToggleSwimlane = this.onToggleSwimlane.bind(this);
        this.onToggleInitiatives = this.onToggleInitiatives.bind(this);
        this.getTasksForCell = this.getTasksForCell.bind(this);
        this.getWipCount = this.getWipCount.bind(this);
        this.onSearchInput = this.onSearchInput.bind(this);
        this.onFilterSwimlane = this.onFilterSwimlane.bind(this);
        this.onFilterUser = this.onFilterUser.bind(this);
        this.onClearFilters = this.onClearFilters.bind(this);

        onWillStart(() => this.loadMultilevelData());
        onWillUpdateProps(() => this.loadMultilevelData());
    }

    // =========================================================================
    // Data loading
    // =========================================================================

    get _context() {
        return this.props.list?.context || {};
    }

    get isPortfolioMode() {
        return !!this._context.portfolio_mode;
    }

    async loadMultilevelData() {
        if (this.isPortfolioMode) {
            await this._loadPortfolioData();
        } else {
            await this._loadSingleProjectData();
        }
        this.multilevel.loaded = true;
    }

    async _loadSingleProjectData() {
        const projectId = this._extractProjectId();
        if (!projectId) {
            this.multilevel.enabled = false;
            return;
        }

        try {
            const [swimlanes, stages, projectData, initiatives] =
                await Promise.all([
                    this.orm.searchRead(
                        "project.kanban.swimlane",
                        [["project_id", "=", projectId]],
                        [
                            "name", "sequence", "color", "icon",
                            "is_expedite", "wip_limit", "fold", "task_count",
                        ],
                        { order: "sequence, id" }
                    ),
                    this.orm.searchRead(
                        "project.task.type",
                        [["project_ids", "in", [projectId]]],
                        [
                            "name", "sequence", "has_sub_stages",
                            "wip_limit", "wip_limit_type", "area_type",
                        ],
                        { order: "sequence, id" }
                    ),
                    this.orm.read("project.project", [projectId], [
                        "use_multilevel_kanban",
                        "show_initiatives_lane",
                    ]),
                    this.orm.searchRead(
                        "project.task",
                        [
                            ["project_id", "=", projectId],
                            ["is_initiative", "=", true],
                        ],
                        [
                            "name", "stage_id", "child_progress_data",
                            "card_size", "swimlane_id",
                        ]
                    ),
                ]);

            const proj = projectData[0] || {};
            this.multilevel.enabled = proj.use_multilevel_kanban || false;
            this.multilevel.swimlanes = swimlanes;
            this.multilevel.stages = stages;
            this.multilevel.projectData = proj;
            this.multilevel.initiatives = initiatives;
        } catch (e) {
            console.error("[KanbanMultilevel] load error:", e);
            this.multilevel.enabled = false;
        }
    }

    async _loadPortfolioData() {
        const projectIds = this._context.portfolio_project_ids || [];
        if (!projectIds.length) {
            this.multilevel.enabled = false;
            return;
        }

        try {
            const [swimlanes, stages, initiatives] = await Promise.all([
                this.orm.searchRead(
                    "project.kanban.swimlane",
                    [["project_id", "in", projectIds]],
                    [
                        "name", "sequence", "color", "icon",
                        "is_expedite", "wip_limit", "fold", "task_count",
                        "project_id",
                    ],
                    { order: "sequence, id" }
                ),
                this.orm.searchRead(
                    "project.task.type",
                    [["project_ids", "in", projectIds]],
                    [
                        "name", "sequence", "has_sub_stages",
                        "wip_limit", "wip_limit_type", "area_type",
                    ],
                    { order: "sequence, id" }
                ),
                this.orm.searchRead(
                    "project.task",
                    [
                        ["project_id", "in", projectIds],
                        ["is_initiative", "=", true],
                    ],
                    [
                        "name", "stage_id", "child_progress_data",
                        "card_size", "swimlane_id",
                    ]
                ),
            ]);

            // Deduplicate stages by name (shared across projects)
            const stageMap = new Map();
            for (const s of stages) {
                if (!stageMap.has(s.id)) {
                    stageMap.set(s.id, s);
                }
            }

            // Deduplicate swimlanes by name (merge across projects)
            const slMap = new Map();
            for (const sl of swimlanes) {
                const key = sl.name;
                if (!slMap.has(key)) {
                    slMap.set(key, { ...sl, _projectIds: [sl.project_id[0]] });
                } else {
                    slMap.get(key)._projectIds.push(sl.project_id[0]);
                }
            }

            this.multilevel.enabled = true;
            this.multilevel.swimlanes = [...slMap.values()];
            this.multilevel.stages = [...stageMap.values()];
            this.multilevel.initiatives = initiatives;
            this.multilevel.projectData = {
                use_multilevel_kanban: true,
                show_initiatives_lane: true,
            };
        } catch (e) {
            console.error("[KanbanMultilevel] portfolio load error:", e);
            this.multilevel.enabled = false;
        }
    }

    _extractProjectId() {
        const ctx = this._context;
        if (ctx.default_project_id) return ctx.default_project_id;
        if (ctx.active_id) return ctx.active_id;
        if (ctx.search_default_project_id) return ctx.search_default_project_id;

        const domain = this.props.list?.domain || [];
        for (const cond of domain) {
            if (
                Array.isArray(cond) &&
                cond[0] === "project_id" &&
                cond[1] === "="
            ) {
                return cond[2];
            }
        }

        // Infer from first record
        const records = this.props.list?.records || [];
        if (records.length > 0) {
            const first = records[0];
            const data = first.data || first;
            const projField = data.project_id;
            if (projField) {
                if (Array.isArray(projField)) return projField[0];
                if (typeof projField === "object" && projField.id) return projField.id;
                if (typeof projField === "number") return projField;
            }
        }

        return null;
    }

    // =========================================================================
    // Getters for template
    // =========================================================================

    get isMultilevel() {
        return this.multilevel.loaded && this.multilevel.enabled;
    }

    get swimlanes() {
        return this.multilevel.swimlanes || [];
    }

    get stages() {
        return this.multilevel.stages || [];
    }

    get initiatives() {
        return this.multilevel.initiatives || [];
    }

    get showInitiatives() {
        return (
            this.multilevel.projectData?.show_initiatives_lane &&
            this.initiatives.length > 0
        );
    }

    get columns() {
        const cols = [];
        for (const stage of this.stages) {
            if (stage.has_sub_stages) {
                cols.push({
                    stageId: stage.id,
                    stageName: stage.name,
                    subStage: "doing",
                    subStageLabel: "Fazendo",
                    isSubColumn: true,
                    wip_limit: stage.wip_limit,
                    wip_limit_type: stage.wip_limit_type,
                    area_type: stage.area_type,
                });
                cols.push({
                    stageId: stage.id,
                    stageName: stage.name,
                    subStage: "done",
                    subStageLabel: "Feito",
                    isSubColumn: true,
                    wip_limit: stage.wip_limit,
                    wip_limit_type: stage.wip_limit_type,
                    area_type: stage.area_type,
                });
            } else {
                cols.push({
                    stageId: stage.id,
                    stageName: stage.name,
                    subStage: null,
                    subStageLabel: null,
                    isSubColumn: false,
                    wip_limit: stage.wip_limit,
                    wip_limit_type: stage.wip_limit_type,
                    area_type: stage.area_type,
                });
            }
        }
        return cols;
    }

    get gridTemplateColumns() {
        const colCount = this.columns.length;
        return `180px repeat(${colCount}, minmax(160px, 1fr))`;
    }

    // =========================================================================
    // Cell data helpers
    // =========================================================================

    _getFieldValue(record, fieldName) {
        const data = record.data || record;
        const val = data[fieldName];
        if (!val) return false;
        // Odoo records: Many2one fields are arrays [id, name] or proxy objects
        if (Array.isArray(val)) return val[0];
        if (typeof val === "object" && val.id) return val.id;
        return val;
    }

    get hasActiveFilters() {
        return !!(
            this.uiState.searchText ||
            this.uiState.filterSwimlaneId !== null ||
            this.uiState.filterUserId !== null
        );
    }

    /**
     * Returns records filtered by search text, swimlane and user.
     */
    get filteredRecords() {
        let records = this.props.list?.records || [];
        const { searchText, filterSwimlaneId, filterUserId } = this.uiState;

        if (searchText) {
            const q = searchText.toLowerCase();
            records = records.filter((r) => {
                const data = r.data || r;
                const name = (data.name || data.display_name || "").toLowerCase();
                const id = String(data.id || r.resId || "");
                return name.includes(q) || id.includes(q);
            });
        }

        if (filterSwimlaneId !== null) {
            records = records.filter((r) => {
                const sl = this._getFieldValue(r, "swimlane_id");
                return sl === filterSwimlaneId;
            });
        }

        if (filterUserId !== null) {
            records = records.filter((r) => {
                const data = r.data || r;
                const userIds = data.user_ids;
                if (!userIds) return false;
                if (userIds.records) {
                    return userIds.records.some(
                        (u) => u.resId === filterUserId
                    );
                }
                if (Array.isArray(userIds)) {
                    return userIds.some((u) =>
                        (Array.isArray(u) ? u[0] : u) === filterUserId
                    );
                }
                return false;
            });
        }

        return records;
    }

    /**
     * Extract unique members from all records for filter dropdown.
     */
    get members() {
        const records = this.props.list?.records || [];
        const memberMap = {};
        for (const r of records) {
            const data = r.data || r;
            const userIds = data.user_ids;
            if (!userIds) continue;
            if (userIds.records) {
                for (const u of userIds.records) {
                    if (u.resId && !memberMap[u.resId]) {
                        memberMap[u.resId] = {
                            id: u.resId,
                            name: u.data?.name || u.data?.display_name || `User ${u.resId}`,
                        };
                    }
                }
            } else if (Array.isArray(userIds)) {
                for (const u of userIds) {
                    const uid = Array.isArray(u) ? u[0] : u;
                    const uname = Array.isArray(u) ? u[1] : `User ${uid}`;
                    if (uid && !memberMap[uid]) {
                        memberMap[uid] = { id: uid, name: uname };
                    }
                }
            }
        }
        return Object.values(memberMap).sort((a, b) => a.name.localeCompare(b.name));
    }

    getTasksForCell(swimlaneId, stageId, subStage) {
        const records = this.filteredRecords;
        return records.filter((r) => {
            const taskSwimlane = this._getFieldValue(r, "swimlane_id");
            const taskStage = this._getFieldValue(r, "stage_id");
            const data = r.data || r;
            const taskSubStage = data.sub_stage || "doing";
            const isInit = data.is_initiative;

            const swimlaneMatch =
                swimlaneId === false
                    ? !taskSwimlane
                    : taskSwimlane === swimlaneId;
            const stageMatch = taskStage === stageId;
            const subStageMatch =
                subStage === null || taskSubStage === subStage;

            return swimlaneMatch && stageMatch && subStageMatch && !isInit;
        });
    }

    getWipCount(stageId, wipLimitType) {
        // WIP always counts all records, not filtered
        const records = this.props.list?.records || [];
        const inStage = records.filter((r) => {
            const taskStage = this._getFieldValue(r, "stage_id");
            const data = r.data || r;
            return taskStage === stageId && !data.is_initiative;
        });
        if (wipLimitType === "size") {
            return inStage.reduce(
                (sum, r) => sum + ((r.data || r).card_size || 1),
                0
            );
        }
        return inStage.length;
    }

    // =========================================================================
    // UI state helpers (collapse / expand)
    // =========================================================================

    isSwimlaneCollapsed(swimlaneId) {
        return !!this.uiState.collapsedSwimlanes[String(swimlaneId)];
    }

    onToggleSwimlane(swimlaneId) {
        const key = String(swimlaneId);
        this.uiState.collapsedSwimlanes[key] =
            !this.uiState.collapsedSwimlanes[key];
    }

    onToggleInitiatives() {
        this.uiState.collapsedInitiatives = !this.uiState.collapsedInitiatives;
    }

    // =========================================================================
    // Actions: drag-and-drop, card click
    // =========================================================================

    async onCardDrop(taskId, target) {
        const vals = {};
        if (target.stageId !== undefined) {
            vals.stage_id = target.stageId;
        }
        if (target.subStage !== undefined) {
            vals.sub_stage = target.subStage;
        }
        if (target.swimlaneId !== undefined) {
            vals.swimlane_id = target.swimlaneId || false;
        }
        await this.orm.write("project.task", [taskId], vals);
        // Reload the model to refresh all records
        await this.props.list.model.load();
        // Also reload multilevel data (initiatives, swimlane counts, etc.)
        await this.loadMultilevelData();
    }

    onCardClick(taskId) {
        // Open detail panel instead of navigating
        this.uiState.selectedTaskId = taskId;
    }

    onClosePanel() {
        this.uiState.selectedTaskId = null;
    }

    onOpenForm(taskId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "project.task",
            res_id: taskId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    get showDetailPanel() {
        return !!this.uiState.selectedTaskId;
    }

    // =========================================================================
    // Filters
    // =========================================================================

    onSearchInput(ev) {
        this.uiState.searchText = ev.target.value;
    }

    onFilterSwimlane(ev) {
        const val = ev.target.value;
        this.uiState.filterSwimlaneId = val === "" ? null : parseInt(val);
    }

    onFilterUser(ev) {
        const val = ev.target.value;
        this.uiState.filterUserId = val === "" ? null : parseInt(val);
    }

    onClearFilters() {
        this.uiState.searchText = "";
        this.uiState.filterSwimlaneId = null;
        this.uiState.filterUserId = null;
    }
}
