# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase

# Agentes nocivos usados nos cenários (Tabela 22 do eSocial).
AGENTE_RUIDO = "l10n_br_esocial.agente_noc_02_01_001"
AGENTE_AUSENCIA = "l10n_br_esocial.agente_noc_09_01_001"


class SstCommon(TransactionCase):
    """Cenário mínimo de SST: ambiente, laudo, risco, empregado e contrato."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        if not cls.company.partner_id.cnpj_cpf:
            cls.company.partner_id.write({"cnpj_cpf": "02.546.716/0001-46"})

        cls.agente_ruido = cls.env.ref(AGENTE_RUIDO)
        cls.agente_ausencia = cls.env.ref(AGENTE_AUSENCIA)
        cls.fin_aposent_25 = cls.env.ref("l10n_br_esocial.fin_aposent_4")
        cls.fin_aposent_15 = cls.env.ref("l10n_br_esocial.fin_aposent_2")

        cls.responsavel = cls.env["l10n_br.sst.responsavel"].create(
            {
                "name": "Engenheiro de Segurança",
                "cpf": "076.166.929-41",
                "ide_oc": "4",
                "nr_oc": "123456",
                "uf_oc": "MG",
            }
        )
        cls.ambiente = cls.env["l10n_br.sst.ambiente"].create(
            {
                "name": "Linha de Envase",
                "dsc_setor": "PRODUCAO",
                "local_amb": "1",
                "tp_insc": "1",
                "nr_insc": "02546716000146",
                "descricao_atividade": "Operação de envasadora automática.",
            }
        )
        cls.job = cls.env["hr.job"].create({"name": "Operador de Envase"})
        cls.job_admin = cls.env["hr.job"].create({"name": "Auxiliar Administrativo"})

        cls.laudo = cls.env["l10n_br.sst.laudo"].create(
            {
                "name": "LTCAT 2026",
                "tipo": "ltcat",
                "date_from": "2026-01-01",
                "responsavel_id": cls.responsavel.id,
            }
        )
        cls.risco = cls.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": cls.ambiente.id,
                "laudo_id": cls.laudo.id,
                "agente_nocivo_id": cls.agente_ruido.id,
                "job_ids": [(6, 0, [cls.job.id])],
                "tp_aval": "1",
                "intensidade": 89.0,
                "limite_tolerancia": 85.0,
                "un_med": "4",
                "tecnica_medicao": "NHO-01",
                "insalubridade": True,
                "grau_insalubridade": "medio",
                "financiamento_aposent_id": cls.fin_aposent_25.id,
                "utiliz_epc": "1",
                "utiliz_epi": "2",
                "efic_epi": "S",
                "date_from": "2026-01-01",
            }
        )

        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Trabalhador SST",
                "cnpj_cpf": "076.166.929-41",
                "job_id": cls.job.id,
            }
        )
        cls.contract = cls.env["hr.contract"].create(
            {
                "name": "Contrato SST",
                "employee_id": cls.employee.id,
                "job_id": cls.job.id,
                "wage": 3000.0,
                "date_start": "2026-01-02",
                "state": "open",
                "l10n_br_sst_ambiente_id": cls.ambiente.id,
            }
        )
