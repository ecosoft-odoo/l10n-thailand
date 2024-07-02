# Copyright 2023 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = "account.account"

    currency_revaluation = fields.Boolean(
        string="Allow Currency Revaluation",
    )

    _sql_mapping = {
        "balance": "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
        "debit": "COALESCE(SUM(debit), 0) as debit",
        "credit": "COALESCE(SUM(credit), 0) as credit",
        "foreign_balance": "COALESCE(SUM(amount_currency), 0) as foreign_balance",
    }

    def init(self):
        # all receivable, payable, Bank and Cash accounts should
        # have currency_revaluation True by default
        res = super().init()
        accounts = self.env["account.account"].search(
            [
                ("user_type_id.id", "in", self._get_revaluation_account_types()),
                ("currency_revaluation", "=", False),
                ("user_type_id.include_initial_balance", "=", True),
            ]
        )
        accounts.write({"currency_revaluation": True})
        return res

    def write(self, vals):
        if (
            "currency_revaluation" in vals
            and vals.get("currency_revaluation", False)
            and any(
                [not x for x in self.mapped("user_type_id.include_initial_balance")]
            )
        ):
            raise UserError(
                _(
                    "There is an account that you are editing not having the Bring "
                    "Balance Forward set, the currency revaluation cannot be applied "
                    "on these accounts: \n\t - %s"
                )
                % "\n\t - ".join(
                    self.filtered(
                        lambda x: not x.user_type_id.include_initial_balance
                    ).mapped("name")
                )
            )
        return super(AccountAccount, self).write(vals)

    def _get_revaluation_account_types(self):
        return [
            self.env.ref("account.data_account_type_receivable").id,
            self.env.ref("account.data_account_type_payable").id,
            self.env.ref("account.data_account_type_liquidity").id,
        ]

    @api.onchange("user_type_id")
    def _onchange_user_type_id(self):
        revaluation_accounts = self._get_revaluation_account_types()
        for rec in self:
            if rec.user_type_id.id in revaluation_accounts:
                rec.currency_revaluation = True

    def _revaluation_query(self, revaluation_date, start_date=None):
        tables, where_clause, where_clause_params = self.env[
            "account.move.line"
        ]._query_get()
        mapping = [
            ('"account_move_line".', "aml."),
            ('"account_move_line"', "account_move_line aml"),
            ("LEFT JOIN", "\n    LEFT JOIN"),
            (")) AND", "))\n" + " " * 12 + "AND"),
        ]
        for s_from, s_to in mapping:
            tables = tables.replace(s_from, s_to)
            where_clause = where_clause.replace(s_from, s_to)
        where_clause = ("\n" + " " * 8 + "AND " + where_clause) if where_clause else ""
        query = (
            """
WITH amount AS (
    SELECT
        aml.id,
        aml.move_name,
        aml.account_id,
        CASE WHEN aat.type IN ('payable', 'receivable')
            THEN aml.partner_id
            ELSE NULL
        END AS partner_id,
        aml.currency_id,
        aml.debit,
        aml.credit,
        aml.amount_currency
    FROM """
            + tables
            + """
    LEFT JOIN account_move am ON aml.move_id = am.id
    INNER JOIN account_account acc ON aml.account_id = acc.id
    INNER JOIN account_account_type aat ON acc.user_type_id = aat.id
    LEFT JOIN account_partial_reconcile aprc
        ON (aml.balance < 0 AND aml.id = aprc.credit_move_id)
    LEFT JOIN account_move_line amlcf
        ON (
            aml.balance < 0
            AND aprc.debit_move_id = amlcf.id
            AND amlcf.date < %s
        )
    LEFT JOIN account_partial_reconcile aprd
        ON (aml.balance > 0 AND aml.id = aprd.debit_move_id)
    LEFT JOIN account_move_line amldf
        ON (
            aml.balance > 0
            AND aprd.credit_move_id = amldf.id
            AND amldf.date < %s
        )
    WHERE
        aml.account_id IN %s
        AND aml.date <= %s
        """
            + (("AND aml.date >= %s") if start_date else "")
            + """
        AND aml.currency_id IS NOT NULL
        AND am.state = 'posted'
        AND aml.balance <> 0
        """
            + where_clause
            + """
    GROUP BY
        aat.type, aml.id
    HAVING
        aml.amount_residual_currency <> 0
)
SELECT
    id,
    move_name,
    account_id,
    partner_id,
    currency_id,"""
            + ", ".join(self._sql_mapping.values())
            + """
FROM amount
GROUP BY
    id,
    move_name,
    account_id,
    currency_id,
    partner_id
ORDER BY account_id, partner_id, currency_id"""
        )

        params = [
            revaluation_date,
            revaluation_date,
            tuple(self.ids),
            revaluation_date,
            *where_clause_params,
        ]
        if start_date:
            # Insert the value after the revaluation date parameter
            params.insert(4, start_date)

        return query, params

    def compute_revaluations(self, revaluation_date, start_date=None):
        query, params = self._revaluation_query(revaluation_date, start_date)
        self.env.cr.execute(query, params)
        lines = self.env.cr.dictfetchall()

        data = {}
        for line in lines:
            account_id, currency_id, partner_id = (
                line["account_id"],
                line["currency_id"],
                line["partner_id"],
            )
            data.setdefault(account_id, {})
            data[account_id].setdefault(partner_id, {})
            if currency_id not in data[account_id][partner_id].keys():
                data[account_id][partner_id][currency_id] = [line]
            else:
                aml = data[account_id][partner_id][currency_id]
                aml.append(line)
                data[account_id][partner_id][currency_id] = aml
        return data