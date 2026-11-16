"""Rename monetary_index_update_selic to monetary_index_update_bacen.

The SELIC module became the module for every Banco Central (SGS) index. Running the
update of monetary_index_update moves the installed SELIC module, its data and its
dependencies to the new name, so the database keeps the same records.
Same steps as openupgradelib.rename_modules, without the extra dependency.
"""

OLD = "monetary_index_update_selic"
NEW = "monetary_index_update_bacen"


def migrate(cr, version):
    cr.execute("SELECT id, state FROM ir_module_module WHERE name = %s", (OLD,))
    old = cr.fetchone()
    if not old or old[1] not in ("installed", "to upgrade"):
        return
    # the module list may already know the new module as uninstalled: drop it
    cr.execute(
        "SELECT id FROM ir_module_module WHERE name = %s AND state = 'uninstalled'",
        (NEW,),
    )
    for (new_id,) in cr.fetchall():
        cr.execute(
            "DELETE FROM ir_module_module_dependency WHERE module_id = %s", (new_id,)
        )
        cr.execute(
            "DELETE FROM ir_model_data WHERE model = 'ir.module.module' AND res_id = %s",
            (new_id,),
        )
        cr.execute("DELETE FROM ir_module_module WHERE id = %s", (new_id,))
    cr.execute(
        "UPDATE ir_module_module SET name = %s, state = 'to upgrade' WHERE name = %s",
        (NEW, OLD),
    )
    cr.execute(
        "UPDATE ir_model_data SET name = %s WHERE module = 'base' AND name = %s",
        ("module_" + NEW, "module_" + OLD),
    )
    cr.execute("UPDATE ir_model_data SET module = %s WHERE module = %s", (NEW, OLD))
    cr.execute(
        "UPDATE ir_module_module_dependency SET name = %s WHERE name = %s", (NEW, OLD)
    )
