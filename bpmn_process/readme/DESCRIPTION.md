Brings BPMN 2.0 process diagrams into Odoo, for implementation projects
that design the solution as BPMN and validate it with the customer.

- Import a `.bpmn` file as it comes (diagram, colors and documentation of
  each element). Each import of the same code is a new version.
- Every task, event and gateway becomes a record, keyed by its BPMN id:
  comments (chatter), status (decided, proposal, open), design reference,
  requirements, link to the Odoo model, menu or action, and end-to-end test
  results. Comments and status survive new versions.
- A diagram viewer (bpmn-js) inside Odoo: click a task to see its panel,
  comment on it, change its status or open the Odoo screen that runs it.
  Layers: status, test results, tasks of the role of the user, original colors.
- Immutable version history with a semantic diff (added, removed, changed,
  moved) and a visual comparison between any two versions.
- An editor with a lock: one manager draws at a time while the others follow
  the changes live and comment.
- Three-way merge: when the diagram changed in Odoo and the file generated
  outside also changed, both are merged by BPMN id, and only the same
  property changed on both sides is a conflict for a person to resolve.
