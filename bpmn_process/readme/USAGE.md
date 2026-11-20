**Import**

Processes > Import BPMN diagram: choose the `.bpmn` file. The code (the file
name by default) identifies the process; importing the same code again
creates a new version and lists the changes in the chatter.

Scripts can import with XML-RPC/JSON-RPC:

```python
env["bpmn.process"].import_xml("P01_sales", xml, note="workshop 2")
```

The result has a `status`: `created`, `updated`, `merged`, `unchanged`,
`conflict` (with the list of conflicts), `invalid` (with the structural
problems) or `locked` (someone is editing). Call again with
`resolutions={"<bpmn id>:<property>": "ours" | "theirs"}` to resolve
conflicts (`ours` is Odoo, `theirs` is the file).

**Documentation of each element**

The `bpmn:documentation` of a task is read line by line:

```
odoo: sale.order / Sales
sdd: 5.2 Quotation
requisitos: COM-04, COM-10
status: decidido | proposta | em aberto
acao: sale.action_quotations_with_onboarding
```

`odoo:` links the task to the model and menu (left empty when ambiguous, to
be filled by hand); `acao:` (optional) names the window action by XML id;
`fora do sistema (...)` marks a task done outside Odoo. The one-line form
`Status: combinado. SDD: 6.2 V2` is also read. On the first import the status
comes from the file; afterwards it belongs to Odoo, and a different status in
a new file is only reported in the version changes.

**Diagram**

Open a process and click *Open diagram*. Click a task to see its panel.
Managers can change the status, and *Edit* opens the modeler with a lock;
*Save version* creates a new version. Versions can be viewed, compared,
downloaded and restored (restoring creates a new version).

**Test results**

End-to-end tests tagged `@bpmn:<id>` report their results with:

```python
env["bpmn.element.test"].record_results([
    {"bpmn_id": "Task_Sales_Quote", "scenario": "quote e2e",
     "result": "passed", "environment": "hml", "process": "P01_sales"},
])
```

**Export**

*Export .bpmn* (or `export_by_code(code)`) returns the current diagram with
the documentation and colors rewritten from the records.
