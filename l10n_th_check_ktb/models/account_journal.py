# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    account_check_printing_layout = fields.Selection(
        selection_add=[("l10n_th_check_ktb.action_report_check_ktb_base", "KTB")],
        ondelete={"l10n_th_check_ktb.action_report_check_ktb_base": "cascade"},
    )
