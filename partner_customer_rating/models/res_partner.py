from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    customer_rating_id = fields.Many2one(
        "customer.rating", string="Satisfação do Cliente", tracking=True
    )

    image_rating = fields.Binary(
        string="Satisfação",
        compute="_compute_image_rating",
    )

    @api.depends("customer_rating_id.image")
    def _compute_image_rating(self):
        for rec in self:
            rec.image_rating = rec.customer_rating_id.image

    @api.model
    def _search_customer_rating(self, operator, value):
        rating_ids = self.env["customer.rating"].search([("name", operator, value)]).ids
        return [("customer_rating_id", "in", rating_ids)]
