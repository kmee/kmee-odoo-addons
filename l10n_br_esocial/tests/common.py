# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

try:
    import esociallib  # noqa: F401

    HAS_ESOCIALLIB = True
except ImportError:
    HAS_ESOCIALLIB = False
    _logger.warning("esociallib não instalada — testes de XML serão pulados")

# Recibo de entrega no formato do leiaute (1.D + 19 dígitos).
RECIBO_S1200 = "1.2.0000000000000012345"
RECIBO_S1210 = "1.2.0000000000000067890"
RECIBO_S1299 = "1.2.0000000000000099999"

NS_5001 = "http://www.esocial.gov.br/schema/evt/evtBasesTrab/v_S_01_03_00"
NS_5011 = "http://www.esocial.gov.br/schema/evt/evtCS/v_S_01_03_00"
NS_5012 = "http://www.esocial.gov.br/schema/evt/evtIrrf/v_S_01_03_00"


class FakeEventoResult:
    """Espelha esociallib.transmissao.EventoResult (mock de retorno)."""

    __slots__ = (
        "event_id",
        "aceito",
        "nr_recibo",
        "code",
        "description",
        "retorno_xml",
    )

    def __init__(
        self,
        event_id,
        aceito=True,
        nr_recibo=None,
        code=None,
        description=None,
        retorno_xml=None,
    ):
        self.event_id = event_id
        self.aceito = aceito
        self.nr_recibo = nr_recibo
        self.code = code
        self.description = description
        self.retorno_xml = retorno_xml


class FakeLoteResult:
    """Espelha esociallib.transmissao.LoteResult (mock de retorno)."""

    def __init__(self, status="processado", eventos=None):
        self.status = status
        self.eventos = eventos or []


def retorno_s5001(cpf, per_apur="2024-03", inss=330.0, base=3000.0, terc=172.5):
    """XML de retorno com o totalizador S-5001 de um trabalhador."""
    return _TEMPLATE_S5001.format(
        ns=NS_5001,
        cpf=cpf,
        per_apur=per_apur,
        inss="%.2f" % inss,
        base="%.2f" % base,
        terc="%.2f" % terc,
        recibo=RECIBO_S1200,
    )


_TEMPLATE_S5001 = """<evento Id="IDBASE1200">
      <retornoEvento>
        <recibo><nrRecibo>{recibo}</nrRecibo></recibo>
        <tot>
          <eSocial xmlns="{ns}">
            <evtBasesTrab Id="ID5001">
              <ideEvento>
                <nrRecArqBase>{recibo}</nrRecArqBase>
                <indApuracao>1</indApuracao>
                <perApur>{per_apur}</perApur>
              </ideEvento>
              <ideEmpregador><tpInsc>1</tpInsc><nrInsc>02546716</nrInsc></ideEmpregador>
              <ideTrabalhador><cpfTrab>{cpf}</cpfTrab></ideTrabalhador>
              <infoCpCalc>
                <tpCR>115601</tpCR>
                <vrCpSeg>{inss}</vrCpSeg>
                <vrDescSeg>{inss}</vrDescSeg>
              </infoCpCalc>
              <infoCp>
                <classTrib>01</classTrib>
                <ideEstabLot>
                  <tpInsc>1</tpInsc>
                  <nrInsc>02546716000146</nrInsc>
                  <codLotacao>LOT001</codLotacao>
                  <infoCategIncid>
                    <matricula>MAT001</matricula>
                    <codCateg>101</codCateg>
                    <indSimples>1</indSimples>
                    <infoBaseCS>
                      <ind13>0</ind13>
                      <tpValor>11</tpValor>
                      <valor>{base}</valor>
                    </infoBaseCS>
                    <calcTerc>
                      <tpCR>115801</tpCR>
                      <vrCsSegTerc>{terc}</vrCsSegTerc>
                      <vrDescTerc>0.00</vrDescTerc>
                    </calcTerc>
                  </infoCategIncid>
                </ideEstabLot>
              </infoCp>
            </evtBasesTrab>
          </eSocial>
        </tot>
      </retornoEvento>
    </evento>"""


def retorno_s5011(per_apur="2024-03", inss_seg=330.0, base=3000.0, patronal=600.0):
    """XML de retorno com o totalizador S-5011 (consolidado do fechamento)."""
    return _TEMPLATE_S5011.format(
        ns=NS_5011,
        per_apur=per_apur,
        inss_seg="%.2f" % inss_seg,
        base="%.2f" % base,
        patronal="%.2f" % patronal,
        recibo=RECIBO_S1299,
    )


_TEMPLATE_S5011 = """<evento Id="IDBASE1299">
      <retornoEvento>
        <recibo><nrRecibo>{recibo}</nrRecibo></recibo>
        <tot>
          <eSocial xmlns="{ns}">
            <evtCS Id="ID5011">
              <ideEvento><indApuracao>1</indApuracao><perApur>{per_apur}</perApur></ideEvento>
              <ideEmpregador><tpInsc>1</tpInsc><nrInsc>02546716</nrInsc></ideEmpregador>
              <infoCS>
                <nrRecArqBase>{recibo}</nrRecArqBase>
                <indExistInfo>1</indExistInfo>
                <infoCPSeg>
                  <vrDescCP>{inss_seg}</vrDescCP>
                  <vrCpSeg>{inss_seg}</vrCpSeg>
                </infoCPSeg>
                <ideEstab>
                  <tpInsc>1</tpInsc>
                  <nrInsc>02546716000146</nrInsc>
                  <ideLotacao>
                    <codLotacao>LOT001</codLotacao>
                    <fpas>515</fpas>
                    <codTercs>0079</codTercs>
                    <basesRemun>
                      <indIncid>1</indIncid>
                      <codCateg>101</codCateg>
                      <basesCp><vrBcCp00>{base}</vrBcCp00></basesCp>
                    </basesRemun>
                  </ideLotacao>
                </ideEstab>
                <infoCRContrib><tpCR>115101</tpCR><vrCR>{patronal}</vrCR></infoCRContrib>
              </infoCS>
            </evtCS>
          </eSocial>
        </tot>
      </retornoEvento>
    </evento>"""


def retorno_s5012(per_apur="2024-03", irrf=85.2):
    """XML de retorno com o totalizador S-5012 (IRRF consolidado)."""
    return _TEMPLATE_S5012.format(
        ns=NS_5012,
        per_apur=per_apur,
        irrf="%.2f" % irrf,
        recibo=RECIBO_S1210,
    )


_TEMPLATE_S5012 = """<evento Id="IDBASE1210">
      <retornoEvento>
        <recibo><nrRecibo>{recibo}</nrRecibo></recibo>
        <tot>
          <eSocial xmlns="{ns}">
            <evtIrrf Id="ID5012">
              <ideEvento><indApuracao>1</indApuracao><perApur>{per_apur}</perApur></ideEvento>
              <ideEmpregador><tpInsc>1</tpInsc><nrInsc>02546716</nrInsc></ideEmpregador>
              <infoIRRF>
                <nrRecArqBase>{recibo}</nrRecArqBase>
                <indExistInfo>1</indExistInfo>
                <infoCRMen><CRMen>056101</CRMen><vrCRMen>{irrf}</vrCRMen></infoCRMen>
              </infoIRRF>
            </evtIrrf>
          </eSocial>
        </tot>
      </retornoEvento>
    </evento>"""


class ESocialCicloCommon(TransactionCase):
    """Cenário mínimo do ciclo periódico: empresa, empregado, holerite."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
                test_queue_job_no_delay=True,
            )
        )
        cls.company = cls.env.company
        if not cls.company.partner_id.cnpj_cpf:
            cls.company.partner_id.write({"cnpj_cpf": "02.546.716/0001-46"})
        cls.company.write(
            {
                "l10n_br_esocial_cod_lotacao": "LOT001",
                "l10n_br_esocial_class_trib_id": cls.env.ref(
                    "l10n_br_esocial.class_trib_01"
                ).id,
                "l10n_br_esocial_lotacao_id": cls.env.ref(
                    "l10n_br_esocial.lot_trib_01"
                ).id,
            }
        )
        cls.cat_101 = cls.env.ref("l10n_br_esocial.cat_trab_101")
        cls.nat_rubr = cls.env.ref("l10n_br_esocial.nat_rubr_1000")

        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Trabalhador Ciclo eSocial",
                "cnpj_cpf": "076.166.929-41",
                "l10n_br_esocial_matricula": "MAT001",
                "l10n_br_esocial_categoria_id": cls.cat_101.id,
            }
        )
        cls.cpf_employee = "07616692941"
        cls.contract = cls.env["hr.contract"].create(
            {
                "name": "Contrato Ciclo eSocial",
                "employee_id": cls.employee.id,
                "wage": 3000.0,
                "date_start": "2024-01-02",
                "state": "open",
            }
        )
        cls.rule = cls.env["hr.salary.rule"].search(
            [("code", "=", "SALARIO_BASE")], limit=1
        ) or cls.env["hr.salary.rule"].search([], limit=1)
        cls.rule.write(
            {
                "l10n_br_esocial_cod_rubr": "SAL_BASE",
                "l10n_br_esocial_ide_tab_rubr": "1",
                "l10n_br_esocial_nat_rubr_id": cls.nat_rubr.id,
                "l10n_br_esocial_tp_rubr": "1",
                "l10n_br_esocial_cod_inc_cp": "11",
                "l10n_br_esocial_cod_inc_irrf": "11",
                "l10n_br_esocial_cod_inc_fgts": "11",
            }
        )

    def _criar_payslip(self, linhas=None, data_pagamento=None, state="done"):
        """Holerite confirmado com as rubricas informadas.

        ``linhas`` é uma lista de tuplas ``(code, valor)`` — os códigos usados
        pela conferência são GROSS, INSS, IRRF e NET.
        """
        if linhas is None:
            linhas = [
                ("GROSS", 3000.0),
                ("INSS", -330.0),
                ("IRRF", -85.2),
                ("NET", 2584.8),
            ]
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Holerite Ciclo 03/2024",
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "date_from": "2024-03-01",
                "date_to": "2024-03-31",
                "state": state,
                "l10n_br_esocial_data_pagamento": data_pagamento,
            }
        )
        for code, valor in linhas:
            self.env["hr.payslip.line"].create(
                {
                    "slip_id": payslip.id,
                    "salary_rule_id": self.rule.id,
                    "name": code,
                    "code": code,
                    "employee_id": self.employee.id,
                    "contract_id": self.contract.id,
                    "quantity": 1,
                    "amount": valor,
                    "rate": 100,
                }
            )
        return payslip

    def _criar_evento(self, tipo, state="success", **kwargs):
        """Evento eSocial em estado arbitrário (atalho para cenários)."""
        vals = {
            "tipo": tipo,
            "company_id": self.company.id,
            "state": state,
        }
        vals.update(kwargs)
        return self.env["l10n_br.esocial.evento"].create(vals)
