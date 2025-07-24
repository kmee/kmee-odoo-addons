# (c) 2025 Kmee - André Marcos Ferreira <andre.ferreira@kmee.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

class ResCurrencyRateProviderBCB(models.Model):
    _inherit = "res.currency.rate.provider"

    service = fields.Selection(
        selection_add=[("BCB", "Brazilian Central Bank")],
        ondelete={"BCB": "set default"},
    )

    @api.model
    def _get_supported_currencies(self):
        self.ensure_one()
        if self.service == "BCB":
            # List of currencies obtained from:
            # https://olinda.bcb.gov.br/olinda/servico/PTAX/versao
            # /v1/odata/Moedas?$top=100&$format=json&$select=simbolo
            return [
                "AUD",
                "CAD",
                "CHF",
                "DKK",
                "EUR",
                "GBP",
                "JPY",
                "NOK",
                "SEK",
                "USD",
                "BRL",
            ]
        return super()._get_supported_currencies()

    @api.model
    def _obtain_rates(self, base_currency, currencies, date_from, date_to):
        self.ensure_one()
        if self.service == "BCB":
            url = (
                "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/"
                "v1/odata/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial"
                "=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?"
                "format=json&skip=0&top=10000&$filter=tipoBoletim%20eq"
                "%20%27Fechamento%27%20or%20tipoBoletim%20eq%20%27Abert"
                "ura%27&select=paridadeCompra%2CparidadeVen"
                "da%2CcotacaoCompra%2CcotacaoVenda%2CdataHoraCotacao%2"
                "CtipoBoletim"
            )
            params = dict()
            params["@dataInicial"] = date_from.strftime("'%m-%d-%Y'")
            params["@dataFinalCotacao"] = date_to.strftime("'%m-%d-%Y'")
            data = {}

            if base_currency == "BRL":
                for cur in currencies:
                    if cur == "BRL":
                        continue
                    params["@moeda"] = "'" + cur + "'"
                    response = requests.get(url, params=params, timeout=10)
                    if response.ok:
                        content = response.json()
                        for rate in content.get("value", []):
                            rate_date = fields.Date.from_string(
                                rate.get("dataHoraCotacao")
                            ).strftime(DEFAULT_SERVER_DATE_FORMAT)
                            if data.get(rate_date):
                                data[rate_date][cur] = 1 / rate.get("cotacaoVenda")
                            else:
                                rate_dict = {cur: 1 / rate.get("cotacaoVenda")}
                                data[rate_date] = rate_dict

            elif "BRL" in currencies:
                params["@moeda"] = "'" + base_currency + "'"
                response = requests.get(url, params=params, timeout=10)
                if response.ok:
                    content = response.json()
                    base_rates = {}
                    for rate in content.get("value", []):
                        rate_date = fields.Date.from_string(
                            rate.get("dataHoraCotacao")
                        ).strftime(DEFAULT_SERVER_DATE_FORMAT)
                        base_rates[rate_date] = rate.get("cotacaoVenda")

                    for rate_date, base_rate in base_rates.items():
                        if base_rate:
                            if data.get(rate_date):
                                data[rate_date]["BRL"] = base_rate
                            else:
                                data[rate_date] = {"BRL": base_rate}

                    for cur in currencies:
                        if cur in ["BRL", base_currency]:
                            continue
                        params["@moeda"] = "'" + cur + "'"
                        response = requests.get(url, params=params, timeout=10)
                        if response.ok:
                            content = response.json()
                            for rate in content.get("value", []):
                                rate_date = fields.Date.from_string(
                                    rate.get("dataHoraCotacao")
                                ).strftime(DEFAULT_SERVER_DATE_FORMAT)
                                if rate_date in base_rates and base_rates[rate_date]:
                                    # Calcular taxa cruzada
                                    cross_rate = rate.get("cotacaoVenda") / base_rates[rate_date]
                                    if data.get(rate_date):
                                        data[rate_date][cur] = cross_rate
                                    else:
                                        data[rate_date] = {cur: cross_rate}

            else:
                raise UserError(
                    _(
                        "Brazilian Central Bank can only provide rates when either "
                        "the base currency is BRL or BRL is one of the target currencies."
                    )
                )

            return data

        return super()._obtain_rates(base_currency, currencies, date_from, date_to)

