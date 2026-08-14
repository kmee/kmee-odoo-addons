# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging

import pytz
from erpbrasil.base.misc import punctuation_rm

from odoo import _, fields, models
from odoo.exceptions import UserError

from . import aej_layout

_logger = logging.getLogger(__name__)


class L10nBrHrApuracaoPeriodo(models.Model):
    """Geração do AEJ e do espelho de ponto a partir da competência apurada."""

    _inherit = "l10n_br.hr.apuracao.periodo"

    aej_file = fields.Binary(
        string="AEJ",
        readonly=True,
        attachment=True,
        copy=False,
    )
    aej_filename = fields.Char(readonly=True, copy=False)
    aej_p7s = fields.Binary(
        string="Assinatura do AEJ (.p7s)",
        readonly=True,
        attachment=True,
        copy=False,
        help="Assinatura CAdES destacada, gerada com o certificado ICP-Brasil "
        "do desenvolvedor do PTRP (arts. 86 a 88).",
    )
    aej_p7s_filename = fields.Char(readonly=True, copy=False)
    aej_date = fields.Datetime(string="AEJ gerado em", readonly=True, copy=False)
    fuso_horas = fields.Float(
        string="Fuso do estabelecimento",
        default=-3.0,
        help="Deslocamento gravado nos campos de data e hora do AEJ.",
    )

    # ------------------------------------------------------------------
    # Identificação do PTRP (registro 08)
    # ------------------------------------------------------------------

    def _dados_ptrp(self):
        """Identificação do Programa de Tratamento de Registro de Ponto.

        Vem de parâmetros do sistema para que o integrador informe os dados da
        sua própria empresa: quem assina o Atestado Técnico (art. 89) é o
        desenvolvedor do PTRP, e é ele que responde pelo arquivo.
        """
        parametro = self.env["ir.config_parameter"].sudo()
        return {
            "tipoReg": "08",
            "nomeProg": parametro.get_param(
                "l10n_br_hr_attendance_aej.ptrp_nome", "Odoo PTRP"
            ),
            "versaoProg": parametro.get_param(
                "l10n_br_hr_attendance_aej.ptrp_versao", "16.0"
            ),
            "tpIdtDesenv": parametro.get_param(
                "l10n_br_hr_attendance_aej.ptrp_tipo_inscricao", "1"
            ),
            "idtDesenv": punctuation_rm(
                parametro.get_param("l10n_br_hr_attendance_aej.ptrp_cnpj", "")
            ),
            "razaoNomeDesenv": parametro.get_param(
                "l10n_br_hr_attendance_aej.ptrp_razao_social", ""
            ),
            "emailDesenv": parametro.get_param(
                "l10n_br_hr_attendance_aej.ptrp_email", ""
            ),
        }

    # ------------------------------------------------------------------
    # Montagem do arquivo
    # ------------------------------------------------------------------

    def _aej_vinculos(self):
        """Funcionários do período, com identificador sequencial no arquivo."""
        self.ensure_one()
        employees = self.dia_ids.mapped("employee_id").sorted("name")
        return {employee: indice for indice, employee in enumerate(employees, start=1)}

    def _aej_reps(self):
        """REPs que originaram marcações do período."""
        self.ensure_one()
        reps = self.dia_ids.mapped("marcacao_ids.rep_id")
        return {rep: indice for indice, rep in enumerate(reps, start=1)}

    def _aej_horarios(self):
        """Horários contratuais distintos usados no período (registro 04).

        Cada combinação de faixas vira um código; dias com escala diferente
        geram códigos diferentes, que é o que o Anexo VI espera.
        """
        self.ensure_one()
        horarios = {}
        for dia in self.dia_ids:
            codigo = dia._codigo_horario_contratual()
            if not codigo or codigo in horarios:
                continue
            fuso = dia._fuso()
            intervalos = [
                (
                    pytz.utc.localize(inicio).astimezone(fuso),
                    pytz.utc.localize(fim).astimezone(fuso),
                )
                for inicio, fim in dia._intervalos_previstos()
            ]
            duracao = sum(
                (fim - inicio).total_seconds() / 60.0 for inicio, fim in intervalos
            )
            valores = {
                "tipoReg": "04",
                "codHorContratual": codigo,
                "durJornada": int(round(duracao)),
            }
            for ordem, (inicio, fim) in enumerate(intervalos, start=1):
                valores["hrEntrada%02d" % ordem] = aej_layout.formata_hora(inicio)
                valores["hrSaida%02d" % ordem] = aej_layout.formata_hora(fim)
            horarios[codigo] = valores
        return horarios

    def _aej_registros_05(self, vinculos, reps, fuso):
        """Marcações tratadas (registro 05).

        Entram inclusive as desconsideradas, com ``tpMarc = "D"`` e o motivo:
        o arquivo tem que mostrar o que foi descartado e por quê, senão o
        tratamento vira caixa-preta.
        """
        self.ensure_one()
        linhas = []
        for dia in self.dia_ids.sorted(lambda d: (d.employee_id.id, d.date)):
            codigo_horario = dia._codigo_horario_contratual()
            marcacoes = dia.marcacao_ids.sorted("datetime_marcacao")
            for marcacao in marcacoes:
                if marcacao.state == "desconsiderada":
                    tipo = "D"
                elif marcacao.tipo_marcacao in ("E", "S"):
                    tipo = marcacao.tipo_marcacao
                else:
                    # Sem pareamento não há como afirmar entrada ou saída; a
                    # marcação entra como desconsiderada com o motivo, em vez
                    # de ser omitida do arquivo.
                    tipo = "D"
                primeira_entrada = tipo == "E" and marcacao.seq_par == 1
                linhas.append(
                    {
                        "tipoReg": "05",
                        "idtVinculoAej": vinculos.get(dia.employee_id, ""),
                        "dataHoraMarc": aej_layout.formata_datetime(
                            marcacao.datetime_marcacao, fuso
                        ),
                        "idRepAej": reps.get(marcacao.rep_id, ""),
                        "tpMarc": tipo,
                        "seqEntSaida": "%03d" % (marcacao.seq_par or 0),
                        "fonteMarc": marcacao.fonte_aej or "T",
                        "codHorContratual": codigo_horario if primeira_entrada else "",
                        "motivo": marcacao.motivo
                        or (
                            _("Marcação sem par no dia")
                            if tipo == "D" and not marcacao.motivo
                            else ""
                        ),
                    }
                )
        return linhas

    def _aej_registros_07(self, vinculos):
        """Ausências e banco de horas (registro 07)."""
        self.ensure_one()
        linhas = []
        for dia in self.dia_ids.sorted(lambda d: (d.employee_id.id, d.date)):
            identificador = vinculos.get(dia.employee_id, "")
            if dia.falta_injustificada:
                linhas.append(
                    {
                        "tipoReg": "07",
                        "idtVinculoAej": identificador,
                        "tipoAusenOuComp": aej_layout.AUSENCIA_FALTA,
                        "data": aej_layout.formata_data(dia.date),
                    }
                )
            elif not dia.jornada_prevista and not dia.feriado:
                linhas.append(
                    {
                        "tipoReg": "07",
                        "idtVinculoAej": identificador,
                        "tipoAusenOuComp": aej_layout.AUSENCIA_DSR,
                        "data": aej_layout.formata_data(dia.date),
                    }
                )
            for ocorrencia in dia.ocorrencia_ids.filtered(
                lambda o: o.tipo_aej == aej_layout.AUSENCIA_FOLGA_FERIADO
            ):
                linhas.append(
                    {
                        "tipoReg": "07",
                        "idtVinculoAej": identificador,
                        "tipoAusenOuComp": ocorrencia.tipo_aej,
                        "data": aej_layout.formata_data(dia.date),
                    }
                )
            if dia.banco_horas_delta:
                minutos = int(round(abs(dia.banco_horas_delta) * 60))
                linhas.append(
                    {
                        "tipoReg": "07",
                        "idtVinculoAej": identificador,
                        "tipoAusenOuComp": aej_layout.AUSENCIA_BANCO_HORAS,
                        "data": aej_layout.formata_data(dia.date),
                        "qtMinutos": minutos,
                        "tipoMovBH": aej_layout.BH_INCLUSAO
                        if dia.banco_horas_delta > 0
                        else aej_layout.BH_COMPENSACAO,
                    }
                )
        return linhas

    def gerar_aej(self):
        """Monta o conteúdo do AEJ do período (RP-20).

        Returns:
            Tupla ``(nome_do_arquivo, conteudo_texto)``.
        """
        self.ensure_one()
        if self.state != "fechado":
            raise UserError(
                _(
                    "Gere o AEJ a partir de competência fechada: o arquivo "
                    "entregue à fiscalização não pode mudar depois de emitido."
                )
            )
        fuso = self.fuso_horas
        empresa = self.company_id
        vinculos = self._aej_vinculos()
        reps = self._aej_reps()
        horarios = self._aej_horarios()

        linhas = []
        contagem = {
            tipo: 0 for tipo in ("01", "02", "03", "04", "05", "06", "07", "08")
        }

        cabecalho = {
            "tipoReg": "01",
            "tpIdtEmpregador": "1",
            "idtEmpregador": punctuation_rm(empresa.cnpj_cpf or ""),
            "caepf": "",
            "cno": "",
            "razaoOuNome": (empresa.name or "")[:150],
            "dataInicialAej": aej_layout.formata_data(self.date_from),
            "dataFinalAej": aej_layout.formata_data(self.date_to),
            "dataHoraGerAej": aej_layout.formata_datetime(fields.Datetime.now(), fuso),
            "versaoAej": aej_layout.VERSAO_LEIAUTE,
        }
        linhas.append(aej_layout.monta_registro("01", cabecalho))
        contagem["01"] += 1

        for rep, identificador in reps.items():
            linhas.append(
                aej_layout.monta_registro(
                    "02",
                    {
                        "tipoReg": "02",
                        "idRepAej": identificador,
                        "tpRep": aej_layout.TIPO_REP_AEJ.get(rep.tipo, "1"),
                        "nrRep": punctuation_rm(rep._identificador_afd()),
                    },
                )
            )
            contagem["02"] += 1

        for employee, identificador in vinculos.items():
            linhas.append(
                aej_layout.monta_registro(
                    "03",
                    {
                        "tipoReg": "03",
                        "idtVinculoAej": identificador,
                        "cpf": punctuation_rm(
                            employee.sudo().cpf or employee.sudo().cnpj_cpf or ""
                        ),
                        "nomeEmp": (employee.name or "")[:150],
                    },
                )
            )
            contagem["03"] += 1

        for valores in horarios.values():
            linhas.append(aej_layout.monta_registro("04", valores))
            contagem["04"] += 1

        for valores in self._aej_registros_05(vinculos, reps, fuso):
            linhas.append(aej_layout.monta_registro("05", valores))
            contagem["05"] += 1

        for valores in self._aej_registros_07(vinculos):
            linhas.append(aej_layout.monta_registro("07", valores))
            contagem["07"] += 1

        linhas.append(aej_layout.monta_registro("08", self._dados_ptrp()))
        contagem["08"] += 1

        trailer = {"tipoReg": "99"}
        for tipo, quantidade in contagem.items():
            trailer["qtRegistrosTipo%s" % tipo] = quantidade
        linhas.append(aej_layout.monta_registro("99", trailer))

        conteudo = aej_layout.TERMINADOR_LINHA.join(linhas)
        conteudo += aej_layout.TERMINADOR_LINHA
        nome = aej_layout.nome_arquivo_aej(
            punctuation_rm(empresa.cnpj_cpf or ""), self.date_from, self.date_to
        )
        return nome, conteudo

    def action_gerar_aej(self):
        """Gera e anexa o AEJ, assinando quando houver certificado (RP-22)."""
        for periodo in self:
            nome, conteudo = periodo.gerar_aej()
            bruto = conteudo.encode(aej_layout.ENCODING_AEJ, errors="replace")
            valores = {
                "aej_filename": nome,
                "aej_file": base64.b64encode(bruto),
                "aej_date": fields.Datetime.now(),
            }
            assinatura = periodo._assinar_aej(bruto)
            if assinatura:
                valores.update(
                    {
                        "aej_p7s": base64.b64encode(assinatura),
                        "aej_p7s_filename": nome + ".p7s",
                    }
                )
            periodo.write(valores)
            periodo.message_post(
                body=_("AEJ gerado: %s") % nome,
                attachments=[(nome, bruto)],
            )
        return True

    def _certificado_ptrp(self):
        """Certificado ICP-Brasil usado para assinar o AEJ.

        Reusa o cadastro de certificado A1 do ``l10n_br_fiscal_certificate``
        quando disponível, em vez de criar um cadastro paralelo de chaves.
        """
        self.ensure_one()
        empresa = self.company_id
        if not hasattr(empresa, "certificate_ecnpj_id"):
            return None
        certificado = empresa.certificate_ecnpj_id or empresa.certificate_ecpf_id
        # ``is_valid`` é calculado e não armazenado: a validade se confere no
        # registro, não no domínio de busca.
        return certificado if certificado and certificado.is_valid else None

    def _assinar_aej(self, conteudo_bruto):
        """Assinatura CAdES destacada (.p7s), quando há certificado.

        Sem certificado configurado o arquivo é gerado mesmo assim: ele já
        serve para conferência interna, e travar a geração deixaria o RH sem
        nada em mãos. A ausência da assinatura fica registrada no chatter.
        """
        self.ensure_one()
        certificado = self._certificado_ptrp()
        if not certificado:
            self.message_post(
                body=_(
                    "AEJ gerado SEM assinatura: não há certificado A1 válido "
                    "cadastrado. Os arts. 86 a 88 da Portaria 671/2021 exigem "
                    "assinatura com certificado ICP-Brasil para a entrega "
                    "oficial."
                )
            )
            return None
        try:
            from erpbrasil.assinatura import certificado as lib_certificado
            from erpbrasil.assinatura.assinatura import Assinatura
        except ImportError:
            _logger.warning(
                "erpbrasil.assinatura indisponível: AEJ gerado sem assinatura."
            )
            return None
        try:
            cert = lib_certificado.Certificado(
                arquivo=base64.b64decode(certificado.file),
                senha=certificado.password,
            )
            return Assinatura(cert).assina_pkcs7(conteudo_bruto)
        except Exception:
            _logger.exception("Falha ao assinar o AEJ do período %s", self.name)
            self.message_post(
                body=_(
                    "Falha ao assinar o AEJ com o certificado cadastrado. O "
                    "arquivo foi gerado sem assinatura; verifique o "
                    "certificado antes da entrega."
                )
            )
            return None

    def action_imprimir_espelho(self):
        """Espelho de ponto do período (RP-21)."""
        self.ensure_one()
        return self.env.ref(
            "l10n_br_hr_attendance_aej.action_report_espelho_ponto"
        ).report_action(self)
