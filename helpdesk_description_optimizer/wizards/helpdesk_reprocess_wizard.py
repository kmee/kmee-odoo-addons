import logging
from uuid import uuid4

from odoo import SUPERUSER_ID, _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HelpdeskReprocessWizard(models.Model):
    _name = "helpdesk.ticket.reprocess.wizard"
    _description = "Assistente para Reprocessar Descrições dos Tickets"

    ticket_count = fields.Integer(
        string="Total de Tickets",
        compute="_compute_ticket_count",
    )
    state = fields.Selection(
        [
            ("draft", "Não iniciado"),
            ("processing", "Processando"),
            ("done", "Concluído"),
        ],
        default="draft",
        required=True,
    )
    processed_count = fields.Integer(
        string="Tickets Processados",
        default=0,
    )
    updated_count = fields.Integer(
        string="Tickets Atualizados",
        default=0,
    )
    log_text = fields.Text(
        string="Log de Processamento",
        readonly=True,
    )
    validation_state = fields.Selection(
        [
            ("draft", "Não validado"),
            ("testing", "Validando"),
            ("success", "Validado"),
            ("failure", "Falhou"),
        ],
        string="Validação da Fila",
        default="draft",
        readonly=True,
    )
    validation_message = fields.Text(
        string="Status da Validação",
        readonly=True,
    )
    validation_job_uuid = fields.Char(
        string="UUID do Job de Validação",
        readonly=True,
    )

    def _get_ticket_model(self):
        """Retorna o nome do modelo de tickets disponível."""
        return "helpdesk.ticket"

    def _compute_ticket_count(self):
        """Calcula total de tickets com descrição."""
        for record in self:
            ticket_model = self._get_ticket_model()
            if ticket_model:
                record.ticket_count = self.env[ticket_model].search_count(
                    [("description", "!=", False)]
                )
            else:
                record.ticket_count = 0

    def _is_jobrunner_enabled(self):
        params = self.env["ir.config_parameter"].sudo()
        runner_enabled = params.get_param("queue_job.jobrunner.runner_enabled")
        return bool(runner_enabled and runner_enabled.lower() in {"1", "true", "yes"})

    def _set_jobrunner_enabled_param(self, enabled):
        self.env["ir.config_parameter"].sudo().set_param(
            "queue_job.jobrunner.runner_enabled",
            "True" if enabled else "False",
        )

    def _queue_job_validation_description(self):
        self.ensure_one()
        return f"Validar queue job wizard #{self.id}"

    def _append_log(self, message):
        self.ensure_one()
        current_log = self.log_text or ""
        self.write(
            {
                "log_text": f"{current_log}{message}\n",
            }
        )

    def _assert_jobrunner_configured(self):
        if not self._is_jobrunner_enabled():
            raise UserError(
                _(
                    "O Job Runner não está habilitado.\n\n"
                    "Para utilizar esta funcionalidade, ative o parâmetro "
                    "'queue_job.jobrunner.runner_enabled' nas configurações do sistema "
                    "e certifique-se de que o serviço do Job Runner está em execução."
                )
            )

    def _get_validation_job(self):
        self.ensure_one()
        if not self.validation_job_uuid:
            return self.env["queue.job"]
        return (
            self.env["queue.job"]
            .sudo()
            .search(
                [("uuid", "=", self.validation_job_uuid)],
                limit=1,
            )
        )

    def _refresh_validation_status(self):
        for wizard in self:
            if not wizard.validation_job_uuid:
                continue

            job = wizard._get_validation_job()
            if not job:
                continue

            if job.state == "done" and wizard.validation_state != "success":
                wizard._set_jobrunner_enabled_param(True)
                wizard.write(
                    {
                        "validation_state": "success",
                        "validation_message": _(
                            "Validação concluída com sucesso. O queue_job está processando jobs."
                        ),
                    }
                )
            elif job.state == "failed":
                wizard._set_jobrunner_enabled_param(False)
                wizard.write(
                    {
                        "validation_state": "failure",
                        "validation_message": _("O job de validação falhou.\n\n%s")
                        % (job.exc_info or job.exc_name or _("Sem detalhes.")),
                    }
                )
            elif job.state in {"pending", "enqueued", "started", "wait_dependencies"}:
                wizard.write(
                    {
                        "validation_state": "testing",
                        "validation_message": _(
                            "Validação em andamento. Aguarde a execução do job de teste e atualize o status."
                        ),
                    }
                )

    def _enqueue_validation_job(self):
        self.ensure_one()
        description = self._queue_job_validation_description()
        token = uuid4().hex

        self.write(
            {
                "validation_state": "testing",
                "validation_message": _(
                    "Job de validação enfileirado. Aguarde a execução e atualize o status."
                ),
                "validation_job_uuid": False,
            }
        )
        self._append_log(_("Validação do queue_job enfileirada."))

        delayed_wizard = self.with_user(SUPERUSER_ID)
        try:
            delayed_wizard.with_delay(description=description)._queue_job_smoke_test(
                token
            )
        except Exception:
            self._set_jobrunner_enabled_param(False)
            self.write(
                {
                    "validation_state": "failure",
                    "validation_message": _(
                        "Não foi possível enfileirar o job de validação."
                    ),
                }
            )
            raise

        job = (
            self.env["queue.job"]
            .sudo()
            .search(
                [("name", "=", description)],
                order="id desc",
                limit=1,
            )
        )
        if job:
            self.write({"validation_job_uuid": job.uuid})
        else:
            self._set_jobrunner_enabled_param(False)
            self.write(
                {
                    "validation_state": "failure",
                    "validation_message": _(
                        "O job de validação não foi encontrado na fila."
                    ),
                }
            )
            raise UserError(
                _(
                    "Erro validação do job. Verifique se o queue_job está instalado e configurado."
                )
            )

    def _queue_job_smoke_test(self, token):
        self.ensure_one()
        self._set_jobrunner_enabled_param(True)
        self.write(
            {
                "validation_state": "success",
                "validation_message": _(
                    "Validação concluída com sucesso. O queue_job está processando jobs."
                ),
            }
        )
        self._append_log(
            _("Validação do queue_job concluída com sucesso. Token: %s", token)
        )
        return True

    def action_validate_queue_job(self):
        wizard = self[0]
        wizard._refresh_validation_status()

        if wizard.validation_state == "testing":
            raise UserError(
                _(
                    "Já existe uma validação em andamento.\n\n"
                    "Aguarde alguns segundos e clique em 'Atualizar Status da Fila'."
                )
            )

        wizard._enqueue_validation_job()

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_refresh_queue_job_validation(self):
        wizard = self[0]
        wizard._refresh_validation_status()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_start_reprocess(self):
        """Inicia o reprocessamento assíncrono dos tickets."""
        wizard = self[0]

        # wizard._assert_jobrunner_configured()
        wizard._refresh_validation_status()

        ticket_model_name = self._get_ticket_model()
        if not ticket_model_name:
            raise UserError(
                _(
                    "Nenhum modelo de helpdesk encontrado.\n\n"
                    "Instale o módulo helpdesk ou helpdesk_mgmt primeiro."
                )
            )

        if wizard.validation_state == "testing":
            raise UserError(
                _(
                    "A validação do queue_job ainda está em andamento.\n\n"
                    "Clique em 'Atualizar Status da Fila' e tente novamente quando a validação concluir."
                )
            )

        if wizard.validation_state != "success":
            wizard._enqueue_validation_job()
            raise UserError(
                _(
                    "Antes do reprocessamento, foi enfileirado um job de teste para validar a fila.\n\n"
                    "Aguarde a conclusão, clique em 'Atualizar Status da Fila' e tente iniciar o reprocessamento."
                )
            )

        wizard.write(
            {
                "state": "processing",
                "processed_count": 0,
                "updated_count": 0,
                "log_text": "Reprocessamento enfileirado. Aguarde a conclusão do job.\n",
            }
        )

        # ✅ Apenas modo assíncrono
        ticket_model = self.env[ticket_model_name].with_user(SUPERUSER_ID)
        ticket_model.with_delay(
            description="Reprocessar descrições de tickets"
        ).reprocess_description_queue_job(wizard.id)

        _logger.info("Job de reprocessamento enfileirado com sucesso.")

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_close(self):
        """Fecha o wizard."""
        return {"type": "ir.actions.act_window_close"}
