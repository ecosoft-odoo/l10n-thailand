# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payments(self):
        payments = super()._create_payments()
        # Guarantee return date = vendor payment date
        active_model = self._context.get("active_model")
        active_id = self._context.get("active_id")
        if active_model == "account.move" and active_id:
            move = self.env[active_model].browse(active_id)
            if move.return_guarantee_ids:
                move.return_guarantee_ids.date_return = self.payment_date
        return payments
