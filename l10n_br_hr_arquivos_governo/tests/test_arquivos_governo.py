# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestDirf(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

    def _create_dirf(self, **kwargs):
        vals = {
            "company_id": self.company.id,
            "ano_referencia": 2025,
            "ano_calendario": 2024,
        }
        vals.update(kwargs)
        return self.env["l10n_br.hr.dirf"].create(vals)

    def test_dirf_create(self):
        """Cria registro DIRF."""
        dirf = self._create_dirf()
        self.assertEqual(dirf.state, "draft")
        self.assertIn("DIRF", dirf.name)

    def test_dirf_workflow(self):
        """Testa transições de estado."""
        dirf = self._create_dirf()
        dirf.action_open()
        self.assertEqual(dirf.state, "open")
        dirf.action_sent()
        self.assertEqual(dirf.state, "sent")
        dirf.action_draft()
        self.assertEqual(dirf.state, "draft")

    def test_dirf_gerar_bloqueado(self):
        """A geração da DIRF está bloqueada: obrigação extinta."""
        dirf = self._create_dirf()
        with self.assertRaises(UserError) as capturado:
            dirf.action_gerar_dirf()
        mensagem = str(capturado.exception)
        self.assertIn("DIRF foi extinta", mensagem)
        self.assertIn("2.181/2024", mensagem)
        self.assertIn("EFD-Reinf", mensagem)
        self.assertIn("DCTFWeb", mensagem)
        # Nada foi gerado e o registro segue em rascunho.
        self.assertFalse(dirf.file_content)
        self.assertFalse(dirf.file_binary)
        self.assertEqual(dirf.state, "draft")

    def test_dirf_gerar_bloqueado_mesmo_com_funcionarios(self):
        """Buscar funcionários continua permitido, gerar não."""
        dirf = self._create_dirf()
        dirf.action_buscar_funcionarios()
        with self.assertRaises(UserError):
            dirf.action_gerar_dirf()

    def test_dirf_retificadora(self):
        """DIRF retificadora tem campo de recibo."""
        dirf = self._create_dirf(retificadora=True, numero_recibo="12345")
        self.assertTrue(dirf.retificadora)
        self.assertEqual(dirf.numero_recibo, "12345")

    def test_dirf_historico_continua_legivel(self):
        """Registro gerado antes da descontinuação segue consultável."""
        conteudo = "DIRF|2020|2019|N||\r\nFIMDirf|"
        dirf = self._create_dirf(
            ano_referencia=2020,
            ano_calendario=2019,
            state="sent",
            file_content=conteudo,
            file_binary=base64.b64encode(conteudo.encode("ascii")),
            file_name="DIRF_2020_HISTORICO.txt",
        )
        dirf.invalidate_recordset()
        lido = self.env["l10n_br.hr.dirf"].search(
            [("id", "=", dirf.id), ("ano_referencia", "=", 2020)]
        )
        self.assertEqual(lido, dirf)
        self.assertEqual(lido.state, "sent")
        self.assertEqual(lido.file_content, conteudo)
        self.assertEqual(
            base64.b64decode(lido.file_binary).decode("ascii"),
            conteudo,
        )
        self.assertEqual(lido.file_name, "DIRF_2020_HISTORICO.txt")


class TestSefip(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

    def _create_sefip(self, **kwargs):
        vals = {
            "company_id": self.company.id,
            "mes": "1",
            "ano": 2024,
        }
        vals.update(kwargs)
        return self.env["l10n_br.hr.sefip"].create(vals)

    def test_sefip_create(self):
        """Cria registro SEFIP."""
        sefip = self._create_sefip()
        self.assertEqual(sefip.state, "draft")
        self.assertIn("SEFIP", sefip.name)

    def test_sefip_gerar_bloqueado(self):
        """A geração da SEFIP está bloqueada: substituída pelo FGTS Digital."""
        sefip = self._create_sefip()
        with self.assertRaises(UserError) as capturado:
            sefip.action_gerar_sefip()
        mensagem = str(capturado.exception)
        self.assertIn("FGTS Digital", mensagem)
        self.assertIn("3.240/2023", mensagem)
        self.assertIn("03/2024", mensagem)
        self.assertIn("DCTFWeb", mensagem)
        self.assertFalse(sefip.file_content)
        self.assertFalse(sefip.payslip_ids)
        self.assertEqual(sefip.state, "draft")

    def test_sefip_workflow(self):
        """Testa transições de estado SEFIP."""
        sefip = self._create_sefip()
        sefip.action_open()
        self.assertEqual(sefip.state, "open")
        sefip.action_sent()
        self.assertEqual(sefip.state, "sent")

    def test_sefip_historico_continua_legivel(self):
        """Registro gerado antes da descontinuação segue consultável."""
        conteudo = "00 HISTORICO SEFIP"
        sefip = self._create_sefip(
            mes="2",
            ano=2023,
            state="sent",
            file_content=conteudo,
            file_binary=base64.b64encode(conteudo.encode("ascii")),
            file_name="SEFIP_02_2023_HISTORICO.txt",
        )
        sefip.invalidate_recordset()
        lido = self.env["l10n_br.hr.sefip"].search(
            [("id", "=", sefip.id), ("ano", "=", 2023)]
        )
        self.assertEqual(lido, sefip)
        self.assertEqual(lido.file_content, conteudo)
        self.assertEqual(
            base64.b64decode(lido.file_binary).decode("ascii"),
            conteudo,
        )


class TestCaged(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

    def _create_caged(self, **kwargs):
        vals = {
            "company_id": self.company.id,
            "mes": "1",
            "ano": 2024,
        }
        vals.update(kwargs)
        return self.env["l10n_br.hr.caged"].create(vals)

    def test_caged_create(self):
        """Cria registro CAGED."""
        caged = self._create_caged()
        self.assertEqual(caged.state, "draft")
        self.assertIn("CAGED", caged.name)

    def test_caged_gerar_bloqueado(self):
        """A geração do CAGED está bloqueada: obrigação extinta."""
        caged = self._create_caged()
        with self.assertRaises(UserError) as capturado:
            caged.action_gerar_caged()
        mensagem = str(capturado.exception)
        self.assertIn("CAGED foi extinto", mensagem)
        self.assertIn("1.127/2019", mensagem)
        self.assertIn("S-2200", mensagem)
        self.assertIn("S-2299", mensagem)
        self.assertFalse(caged.file_content)
        self.assertFalse(caged.contract_ids)
        self.assertEqual(caged.state, "draft")

    def test_caged_workflow(self):
        """Testa transições de estado CAGED."""
        caged = self._create_caged()
        caged.action_open()
        self.assertEqual(caged.state, "open")
        caged.action_sent()
        self.assertEqual(caged.state, "sent")

    def test_caged_historico_continua_legivel(self):
        """Registro gerado antes da descontinuação segue consultável."""
        conteudo = "A100001HISTORICO CAGED"
        caged = self._create_caged(
            mes="3",
            ano=2019,
            state="sent",
            file_content=conteudo,
            file_binary=base64.b64encode(conteudo.encode("ascii")),
            file_name="CAGED_03_2019_HISTORICO.txt",
        )
        caged.invalidate_recordset()
        lido = self.env["l10n_br.hr.caged"].search(
            [("id", "=", caged.id), ("ano", "=", 2019)]
        )
        self.assertEqual(lido, caged)
        self.assertEqual(lido.file_content, conteudo)
        self.assertEqual(
            base64.b64decode(lido.file_binary).decode("ascii"),
            conteudo,
        )

    def test_constantes_categorias(self):
        """Verifica que constantes de categoria estão carregadas."""
        from ..models.constantes_rh import (
            CATEGORIA_TRABALHADOR,
            SEFIP_CATEGORIA_TRABALHADOR,
        )

        self.assertTrue(len(CATEGORIA_TRABALHADOR) > 20)
        self.assertEqual(SEFIP_CATEGORIA_TRABALHADOR["103"], "07")  # aprendiz
        self.assertEqual(SEFIP_CATEGORIA_TRABALHADOR["721"], "11")  # diretor s/ FGTS
