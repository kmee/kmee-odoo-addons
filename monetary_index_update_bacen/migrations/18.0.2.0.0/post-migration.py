"""From monetary_index_update_selic to monetary_index_update_bacen.

The module record itself is renamed by the pre-migration of monetary_index_update.
Here the SELIC index (noupdate data) gets its SGS code and the cron starts updating
every index with an SGS code.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE monetary_index mi
           SET bcb_sgs_code = '4390'
          FROM ir_model_data imd
         WHERE imd.module = 'monetary_index_update_bacen'
           AND imd.name = 'monetary_index_selic'
           AND imd.model = 'monetary.index'
           AND imd.res_id = mi.id
           AND mi.bcb_sgs_code IS NULL
        """
    )
    cr.execute(
        """
        UPDATE ir_act_server ias
           SET code = 'model.cron_update_rates()'
          FROM ir_cron ic
          JOIN ir_model_data imd
            ON imd.model = 'ir.cron' AND imd.res_id = ic.id
         WHERE ic.ir_actions_server_id = ias.id
           AND imd.module = 'monetary_index_update_bacen'
           AND imd.name = 'ir_cron_update_selic_rates'
           AND ias.code = 'model.cron_update_selic_rates()'
        """
    )
