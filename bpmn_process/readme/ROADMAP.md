- Simultaneous editing by several people (CRDT over the Odoo bus) is not
  included: the editor works with a lock. It needs an experiment with real
  diagrams first.
- Customers comment as internal users; portal access is not included.
- The editor has no properties panel: status, references and links are
  edited in the side panel and in the element form, and written back to the
  documentation on export.
- bpmn-js 17.11.1 is bundled in `static/lib/bpmn-js` (MIT license; the
  bpmn.io watermark must stay visible on the diagram).
