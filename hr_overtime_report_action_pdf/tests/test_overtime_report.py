# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged

REPORT_XMLID = "hr_overtime_report_action_pdf.action_report_overtime"
TEMPLATE_NAME = "hr_overtime_report_action_pdf.report_overtime_document"


@tagged("post_install", "-at_install")
class TestOvertimeReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.employee_a = cls.env["hr.employee"].create({"name": "Funcionario Alfa"})
        cls.employee_b = cls.env["hr.employee"].create({"name": "Funcionario Beta"})
        cls.overtime_a = cls._overtime(cls.employee_a, "2026-03-02", 2.5)
        cls.overtime_b = cls._overtime(cls.employee_b, "2026-03-03", 0.0)
        cls.report = cls.env.ref(REPORT_XMLID)

    @classmethod
    def _overtime(cls, employee, date, hours):
        overtime = cls.env["hr.attendance.overtime"].create(
            {
                "employee_id": employee.id,
                "date": date,
                "duration": hours,
                "duration_real": hours,
            }
        )
        overtime.extra_hours_without_multiplier = hours
        return overtime

    def _html(self, overtimes):
        html, report_type = self.env["ir.actions.report"]._render_qweb_html(
            REPORT_XMLID, overtimes.ids
        )
        self.assertEqual(report_type, "html")
        return html.decode()

    def test_report_is_a_pdf_bound_to_overtime(self):
        """
        Dado o modulo instalado
        Quando se le a acao de relatorio
        Entao e um qweb-pdf sobre hr.attendance.overtime com o template do modulo
        """
        self.assertEqual(self.report.report_type, "qweb-pdf")
        self.assertEqual(self.report.model, "hr.attendance.overtime")
        self.assertEqual(self.report.report_name, TEMPLATE_NAME)

    def test_action_print_pdf_returns_report_action(self):
        """
        Dado dois registros de hora extra
        Quando action_print_pdf e chamada
        Entao devolve a acao do relatorio com os ids dos registros
        """
        overtimes = (self.overtime_a | self.overtime_b).with_context(
            discard_logo_check=True
        )
        action = overtimes.action_print_pdf()
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(action["report_name"], TEMPLATE_NAME)
        self.assertEqual(action["report_type"], "qweb-pdf")
        self.assertEqual(action["context"]["active_ids"], overtimes.ids)

    def test_server_action_is_bound_to_overtime_list(self):
        """
        Dado o menu Acoes da lista de horas extras
        Quando as acoes vinculadas ao modelo sao lidas
        Entao 'Exportar PDF' esta entre elas
        """
        bindings = self.env["ir.actions.actions"].get_bindings("hr.attendance.overtime")
        names = [action["name"] for action in bindings.get("action", [])]
        self.assertIn("Exportar PDF", names)

    def test_server_action_prints_the_selected_records(self):
        """
        Dado dois registros selecionados na lista
        Quando a acao 'Exportar PDF' e executada
        Entao devolve a acao do relatorio so com os selecionados
        """
        server_action = self.env.ref(
            "hr_overtime_report_action_pdf.action_server_print_pdf"
        )
        action = server_action.with_context(
            discard_logo_check=True,
            active_model="hr.attendance.overtime",
            active_ids=self.overtime_a.ids,
            active_id=self.overtime_a.id,
        ).run()
        self.assertEqual(action["report_name"], TEMPLATE_NAME)
        self.assertEqual(action["context"]["active_ids"], self.overtime_a.ids)

    def test_rendered_report_lists_employee_date_and_hours(self):
        """
        Dado uma hora extra de 2.5 h do Funcionario Alfa em 02/03/2026
        Quando o relatorio e renderizado
        Entao aparecem titulo, data, funcionario e horas
        """
        html = self._html(self.overtime_a)
        self.assertIn("Relatório de Horas Extras", html)
        self.assertIn("Funcionario Alfa", html)
        self.assertIn("2026-03-02", html)
        self.assertIn("2.5", html)

    def test_rendered_report_has_one_row_per_record(self):
        """
        Dado dois registros de funcionarios diferentes
        Quando o relatorio e renderizado
        Entao ambos aparecem e a hora zerada vira 0 (nao em branco)
        """
        html = self._html(self.overtime_a | self.overtime_b)
        self.assertIn("Funcionario Alfa", html)
        self.assertIn("Funcionario Beta", html)
        self.assertIn(">0<", html.replace(" ", "").replace("\n", ""))

    def test_rendered_report_only_contains_requested_records(self):
        """
        Dado dois registros existentes
        Quando so um e pedido no relatorio
        Entao o outro funcionario nao aparece
        """
        html = self._html(self.overtime_a)
        self.assertNotIn("Funcionario Beta", html)
