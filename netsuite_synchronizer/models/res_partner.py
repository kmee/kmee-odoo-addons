# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json

import requests

from odoo import api, fields, models


class ResPartner(models.Model):

    _inherit = "res.partner"

    # Campos extras para vincular ao NetSuite
    netsuite_internal_id = fields.Char(index=True)  # ID interno do NetSuite
    netsuite_fin_status = fields.Char()  # Situação Financeira trazida do NetSuite

    # Monta o cabeçalho NLAuth (autenticação mais simples do NetSuite)
    @api.model
    def _ns_headers_nlauth(self, account_id, email, password, role_id):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "NLAuth": "true",
            "Authorization": (
                "NLAuth nlauth_account=%s,nlauth_email=%s,"
                "nlauth_signature=%s,nlauth_role=%s"
                % (account_id, email, password, role_id)
            ),
        }

    # Faz a chamada ao RESTlet para buscar os dados
    @api.model
    def _ns_fetch_fin_status(self):
        ICP = self.env["ir.config_parameter"].sudo()
        url = ICP.get_param("netsuite_synchronizer.netsuite_restlet_url")
        account_id = ICP.get_param("netsuite_synchronizer.netsuite_account_id")
        email = ICP.get_param("netsuite_synchronizer.netsuite_email")
        password = ICP.get_param("netsuite_synchronizer.netsuite_password")
        role_id = ICP.get_param("netsuite_synchronizer.netsuite_role_id")
        fin_field = (
            ICP.get_param("netsuite_synchronizer.netsuite_fin_field")
            or "custentity_fin_status"
        )
        saved_search_id = (
            ICP.get_param("netsuite_synchronizer.netsuite_saved_search_id") or ""
        )

        # Se faltarem parâmetros, não faz nada
        if not url or not account_id or not email or not password or not role_id:
            return []

        # Payload enviado ao RESTlet
        payload = {
            "saved_search_id": saved_search_id,
            "fields": [
                fin_field,
                "internalid",
                "entityid",
                "email",
                "companyname",
                "firstname",
                "lastname",
            ],
        }

        # Chamada HTTP POST
        r = requests.post(
            url,
            headers=self._ns_headers_nlauth(account_id, email, password, role_id),
            data=json.dumps(payload),
            timeout=60,
        )

        # Se não for 200, aborta
        if r.status_code != 200:
            return []

        # Tenta converter resposta em JSON
        try:
            data = r.json()
        except Exception:
            return []

        # Espera receber uma lista de registros
        if not isinstance(data, list):
            return []

        # Normaliza os registros em uma lista de dicts
        res = []
        for row in data:
            rec = {}
            rec["internalid"] = str(row.get("internalid") or "")
            rec["name"] = (
                row.get("entityid")
                or row.get("companyname")
                or (
                    str(row.get("firstname") or "")
                    + " "
                    + str(row.get("lastname") or "")
                ).strip()
            )
            rec["email"] = row.get("email") or ""
            rec["fin"] = row.get(fin_field) or ""
            res.append(rec)
        return res

    # Método chamado pelo CRON: busca no NetSuite e atualiza res.partner
    @api.model
    def cron_netsuite_pull_fin_status(self):
        rows = self._ns_fetch_fin_status()
        if not rows:
            return
        for rec in rows:
            # Critério de busca: internalid primeiro, se não tiver, email
            domain = []
            if rec.get("internalid"):
                domain = [("netsuite_internal_id", "=", rec["internalid"])]
            elif rec.get("email"):
                domain = [("email", "=", rec["email"])]
            else:
                continue

            partner = self.search(domain, limit=1)
            vals = {}

            # Se for criar um novo, usa o name
            if rec.get("name") and not partner:
                vals["name"] = rec["name"]
            if rec.get("email"):
                vals["email"] = rec["email"]
            if rec.get("internalid"):
                vals["netsuite_internal_id"] = rec["internalid"]
            if rec.get("fin") is not None:
                vals["netsuite_fin_status"] = rec["fin"]

            # Atualiza se já existe, cria se não
            if partner:
                partner.write(vals)
            else:
                self.create(vals)
