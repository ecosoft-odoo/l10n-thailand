# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseType(models.Model):
    _name = "purchase.type"
    _description = "Type of purchase"
    _order = "sequence"

    name = fields.Char(
        string="Name",
        required=True,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    description = fields.Text(
        string="Description",
        translate=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    to_create = fields.Selection(
        selection=[
            ("purchase_agreement", "Purchase Agreement"),
            ("expense", "Expense"),
        ],
        string="To Create",
        required=True,
        help="Create purchase agreement or expense when pr is approved",
    )
    is_check_cost = fields.Boolean(
        string="Check Cost",
        default=False,
        help="Check estimated cost on the purchase request",
    )
    max_cost = fields.Float(
        string="Max Cost",
        default=0.0,
        help="Visible when is_check_cost is True, "
        "This field will check with estimated cost must not over max cost",
    )
    is_default = fields.Boolean(
        string="Default",
        default=False,
        help="Default purchase type on the purchase request",
    )
    procurement_method_ids = fields.Many2many(
        comodel_name="procurement.method",
        string="Allowed Procurement Method",
        required=True,
        help="This field will help to filter procurement method in each purchase type "
        "on the purchase request",
    )

    @api.constrains("active", "is_default")
    def _check_is_default(self):
        purchase_types = self.env["purchase.type"].search([("is_default", "=", True)])
        if len(purchase_types) > 1:
            raise UserError(_("Purchase type must have only one default."))
