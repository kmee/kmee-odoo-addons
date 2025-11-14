import logging

from lxml import etree

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TestViewRunner(models.TransientModel):
    _name = "test.view.runner"
    _description = "Runtime form view validator"

    @api.model
    def run_view_test(self, views=False, run_global=False):
        _logger.warning("-------------------------------------------------------------")
        _logger.warning("Starting FULL form view validation using Form()-like logic")

        if run_global:
            views = self._select_views_to_test(all=True)
        elif not views:
            views = self._select_views_to_test(all=False)
        else:
            views = self._browse_filtered_list(views)
        errors = []

        for view in views:
            rec = self._setup_records(view)
            if not rec:
                _logger.warning(
                    "Skipping view %s (%s) as no records found",
                    view.name,
                    view.id,
                )
                continue

            arch_node, fields = self._setup_view(view, rec)

            try:
                self._trigger_computes(rec, fields)
                model_fields = self.env[view.model]._fields
                self._validate_modifiers_recursive(arch_node, model_fields, rec)
            except Exception as e:
                errors.append(
                    f"View '{view.name}' (ID={view.id}, model={view.model}, type={view.type}) "
                    f"failed validation on record ID={rec.ids}:\n{e}"
                )
                # Reset transaction so next view test runs clean
                self.env.cr.rollback()
                continue

        _logger.warning("The form view successfully validated for %s", view.name)
        _logger.warning("-------------------------------------------------------------")

        errors = self._filter_errors(errors)

        if errors:
            error_msg = f"Tested {len(views)} views with {len(errors)} errors:\n\n"
            error_msg += "\n\n".join(errors)
            raise UserError(error_msg)

    def _filter_errors(self, errors):
        filtered_errors = []
        ignore_phrases = [
            "Unknown field 'x_studio_'",
            "Invalid modifier 'invisible' on field 'x_studio_'",
            "Invalid modifier 'column_invisible'",
            "Unknown field 'sel_groups_",
            "Invalid field res.users.sel_groups_",
        ]
        for error in errors:
            if any(phrase in error for phrase in ignore_phrases):
                continue
            filtered_errors.append(error)
        return filtered_errors

    def _browse_filtered_list(self, ids):
        items = self.env["test.view.item"].browse(ids)
        views = []
        for item in items:
            try:
                views.append(self.env.ref(item.view_xml_id))
            except Exception:
                continue
        return views

    def _get_filtered_list(self):
        items = self.env["test.view.item"].search([])
        views = []
        for item in items:
            try:
                views.append(self.env.ref(item.view_xml_id))
            except Exception:
                continue
        return views

    def _get_all_views(self):
        views = self.env["ir.ui.view"].search(
            [
                ("type", "in", ["form", "tree", "kanban"]),
                ("active", "=", True),
            ],
            order="model asc",
        )
        return views

    def _select_views_to_test(self, all=False):
        if all:
            views = self._get_all_views()
        else:
            views = self._get_filtered_list()
        if not views:
            raise UserError(_("No active form views found."))
        return views

    def _setup_records(self, view):
        is_form = view.type == "form"
        limit = 30 if not is_form else 1
        try:
            rec = self.env[view.model].search([], limit=limit)
        except Exception:
            return False
        return rec

    def _setup_view(self, view, rec):
        result = rec.fields_view_get(
            view_id=view.id,
            view_type=view.type,
        )
        arch = result["arch"]
        fields = result["fields"]
        arch_node = etree.fromstring(arch.encode("utf-8"))

        return arch_node, fields

    # -------------------------------------------------------------------------
    # Modifier validation engine (server-side JS emulator)
    # -------------------------------------------------------------------------
    def _validate_modifiers_recursive(self, node, fields, record):
        """
        Simulate the frontend's modifier evaluation (invisible, readonly, required).
        """

        # handle field nodes
        if node.tag == "field":
            field_name = node.get("name")
            if field_name not in fields and "sel_groups_" not in field_name:
                raise UserError(
                    f"Unknown field '{field_name}' in the view architecture"
                )

            # check JS-style modifiers (attrs)
            attrs = node.get("attrs")
            if attrs:
                self._validate_attrs(node, attrs, record)

        # recursively validate children
        for child in node:
            self._validate_modifiers_recursive(child, fields, record)

    def _validate_attrs(self, node, attrs, record):
        """Validate attrs="{'invisible': [('foo', '=', 1)]}" with record context."""
        from odoo.tools.safe_eval import safe_eval

        try:
            parsed = safe_eval(attrs, {})
        except Exception as e:
            raise UserError(
                f"Invalid attrs syntax in field '{node.get('name')}': {e}"
            ) from e

        for modifier_name, domain_expr in parsed.items():
            norm_domain = self._normalize_domain(domain_expr)
            if isinstance(norm_domain, list):
                # domain-style modifier → validate domain
                try:
                    # this catches unknown fields, invalid operators, etc.
                    record.search(norm_domain).ids
                except Exception as e:
                    raise UserError(
                        f"Invalid modifier '{modifier_name}' on field "
                        f"'{node.get('name')}':\n{e}"
                    ) from e

    def _normalize_domain(self, domain):
        # Caso o domínio seja booleano ou string simples, retorne como está
        if not isinstance(domain, (list, tuple)):
            return domain

        new_domain = []
        for term in domain:
            # operadores lógicos como '|', '&', '!' → manter como estão
            if term in ("|", "&", "!"):
                new_domain.append(term)
                continue

            # termo normal de domínio
            if isinstance(term, (list, tuple)) and len(term) == 3:
                field, op, value = term

                # normalizar "in" / "not in" quando value é string
                if op in ("in", "not in") and isinstance(value, str):
                    value = [value]

                new_domain.append((field, op, value))
            else:
                # qualquer coisa inesperada → mantém
                new_domain.append(term)

        return new_domain

    def _trigger_computes(self, rec, fields):
        """Force computation of all computed fields by reading them.

        This exposes compute-time errors just like the UI would.
        """
        if len(rec) != 1:
            rec = rec[:1]
        for fname, finfo in fields.items():
            if finfo.get("depends", False) or finfo.get("compute", False):
                try:
                    # Accessing rec[fname] triggers compute field evaluation
                    _ = rec[fname]
                except Exception as e:
                    raise UserError(
                        f"Error computing field '{fname}' on model '{rec._name}' "
                        f"for record ID {rec.id}:\n{e}"
                    ) from e
