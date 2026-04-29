/**
 * Helpdesk Description Optimizer
 *
 * Funcionalidades:
 * 1. Colapsar threads de e-mail (elementos com data-o-mail-quote)
 * 2. Adicionar botão "Ver histórico" para expandir
 * 3. Lazy loading de imagens
 * 4. Carregar descrição completa via RPC quando data-has-full estiver presente
 */

odoo.define("helpdesk_description_optimizer.description_optimizer", function (require) {
    const rpc = require("web.rpc");
    const initializedContainers = new WeakSet();
    const initializedRecords = new Set();
    const recordStates = new Map();

    function getRecordState(recordId, container) {
        if (!recordStates.has(recordId)) {
            recordStates.set(recordId, {
                currentView: "summary",
                fullHtml: null,
                isLoadingFull: false,
                summaryHtml: container.innerHTML,
            });
        }

        return recordStates.get(recordId);
    }

    function getCurrentHelpdeskTicketId() {
        const hash = window.location.hash || "";
        const params = new URLSearchParams(hash.replace(/^#/, ""));
        if (params.get("model") !== "helpdesk.ticket") {
            return null;
        }
        const recordId = parseInt(params.get("id"), 10);
        return Number.isNaN(recordId) ? null : recordId;
    }

    function getDescriptionContainer() {
        const selectors = [
            '.o_form_view .tab-pane[name="description"] .o_field_html .note-editable',
            '.o_form_view .tab-pane[name="description"] .o_field_html',
            ".o_form_view .o_notebook .tab-content .o_field_html .note-editable",
            ".o_form_view .o_notebook .tab-content .o_field_html",
        ];

        for (const selector of selectors) {
            const container = document.querySelector(selector);
            if (container) {
                return container;
            }
        }

        return null;
    }

    async function getTicketOptimizationFlags(recordId) {
        const result = await rpc.query({
            model: "helpdesk.ticket",
            method: "read",
            args: [[recordId], ["has_description_full"]],
        });
        return result && result[0] ? result[0] : {};
    }

    async function loadFullDescriptionInChunks(recordId) {
        let offset = 0;
        let html = "";

        while (offset !== false) {
            const result = await rpc.query({
                model: "helpdesk.ticket",
                method: "load_description_full_chunk",
                args: [[parseInt(recordId, 10)], offset, 25],
            });

            html += result.html || "";
            offset = result.next_offset;
        }

        return html;
    }

    /**
     * Inicializa o otimizador de descrição em um elemento HTML
     * @param {HTMLElement} container - Elemento DOM que contém a descrição
     */
    async function initDescriptionOptimizer(container) {
        if (!container || initializedContainers.has(container)) return;
        const recordId = container.getAttribute("data-record-id");
        if (!recordId) return;

        const state = getRecordState(recordId, container);

        // 1. Colapsar threads de e-mail
        const quotedElements = container.querySelectorAll('[data-o-mail-quote="1"]');
        if (quotedElements.length > 0) {
            // Ocultar todos os elementos de citação
            quotedElements.forEach((el) => {
                el.style.display = "none";
            });

            // Criar botão "Ver histórico" após o último elemento colapsado
            const lastQuoted = quotedElements[quotedElements.length - 1];
            const existingHistoryBtn =
                container.parentNode.querySelector(".o_show_history_btn");

            if (!existingHistoryBtn) {
                const showHistoryBtn = document.createElement("button");
                showHistoryBtn.className = "o_show_history_btn btn btn-link";
                showHistoryBtn.textContent = "Ver histórico";
                showHistoryBtn.style.marginTop = "10px";

                showHistoryBtn.addEventListener("click", function () {
                    quotedElements.forEach((el) => {
                        el.style.display = "";
                    });
                    showHistoryBtn.style.display = "none";
                });

                lastQuoted.parentNode.insertBefore(
                    showHistoryBtn,
                    lastQuoted.nextSibling
                );
            }
        }

        // 2. Lazy loading de imagens
        const images = container.querySelectorAll("img");
        images.forEach((img) => {
            img.setAttribute("loading", "lazy");
        });

        // 3. Botão "Ver conteúdo completo" se data-has-full estiver presente
        const hasFull = container.getAttribute("data-has-full");

        if (hasFull === "1" && recordId) {
            let loadFullBtn = container.parentNode.querySelector(
                ".o_load_full_description_btn"
            );

            if (!loadFullBtn) {
                loadFullBtn = document.createElement("button");
                loadFullBtn.className = "o_load_full_description_btn btn btn-primary";
                loadFullBtn.style.marginTop = "10px";

                loadFullBtn.addEventListener("click", async function () {
                    try {
                        if (state.currentView === "full") {
                            container.innerHTML = state.summaryHtml;
                            state.currentView = "summary";
                            loadFullBtn.textContent = "Ver conteúdo completo";
                            initializedContainers.delete(container);
                            await initDescriptionOptimizer(container);
                            return;
                        }

                        if (state.fullHtml) {
                            container.innerHTML = state.fullHtml;
                            state.currentView = "full";
                            loadFullBtn.textContent = "Ver resumo";
                            initializedContainers.delete(container);
                            await initDescriptionOptimizer(container);
                            return;
                        }

                        state.summaryHtml = container.innerHTML;
                        state.currentView = "full";
                        state.isLoadingFull = true;
                        loadFullBtn.textContent = "Ver resumo";
                        const fullHtml = await loadFullDescriptionInChunks(recordId);

                        if (fullHtml) {
                            state.fullHtml = fullHtml;
                            container.innerHTML = fullHtml;
                            state.isLoadingFull = false;
                            state.currentView = "full";
                            container.setAttribute("data-full-loaded", "1");
                            loadFullBtn.textContent = "Ver resumo";
                            initializedContainers.delete(container);
                            await initDescriptionOptimizer(container);
                        } else {
                            state.isLoadingFull = false;
                            state.currentView = "summary";
                            loadFullBtn.textContent = "Ver conteúdo completo";
                        }
                    } catch (error) {
                        state.isLoadingFull = false;
                        state.currentView = "summary";
                        loadFullBtn.textContent = "Ver conteúdo completo";
                        console.error("Erro ao carregar descrição completa:", error);
                    }
                });

                container.parentNode.insertBefore(loadFullBtn, container.nextSibling);
            }

            if (state.isLoadingFull) {
                loadFullBtn.textContent = "Ver resumo";
            } else {
                loadFullBtn.textContent =
                    state.currentView === "full"
                        ? "Ver resumo"
                        : "Ver conteúdo completo";
            }
        }

        initializedContainers.add(container);
    }

    async function bootstrapDescriptionOptimizer() {
        const recordId = getCurrentHelpdeskTicketId();
        if (!recordId) {
            return;
        }

        const container = getDescriptionContainer();
        if (!container) {
            return;
        }

        const previousRecordId = container.getAttribute("data-record-id");
        if (previousRecordId !== String(recordId)) {
            container.removeAttribute("data-full-loaded");
            initializedContainers.delete(container);
        }

        container.setAttribute("data-record-id", String(recordId));

        if (!initializedRecords.has(recordId)) {
            try {
                const flags = await getTicketOptimizationFlags(recordId);
                if (flags.has_description_full) {
                    container.setAttribute("data-has-full", "1");
                } else {
                    container.removeAttribute("data-has-full");
                }
                initializedRecords.add(recordId);
            } catch (error) {
                console.error("Erro ao buscar flags da descrição:", error);
                return;
            }
        }

        await initDescriptionOptimizer(container);
    }

    document.addEventListener("DOMContentLoaded", bootstrapDescriptionOptimizer);
    window.addEventListener("hashchange", function () {
        window.setTimeout(bootstrapDescriptionOptimizer, 300);
    });
    window.setInterval(bootstrapDescriptionOptimizer, 1000);

    const observer = new MutationObserver(function () {
        bootstrapDescriptionOptimizer();
    });
    observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
    });

    // Exportar função para uso externo
    return {
        initDescriptionOptimizer: initDescriptionOptimizer,
        bootstrapDescriptionOptimizer: bootstrapDescriptionOptimizer,
    };
});
