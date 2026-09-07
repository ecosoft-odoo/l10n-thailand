# Copyright 2019 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models
from odoo.tools.float_utils import float_is_zero


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    @api.model
    def _prepare_cash_basis_tax_line_vals(self, tax_line, balance, amount_currency):
        """Prorate the tax base amount of the cash basis tax line.

        Odoo copies the full tax base of the origin document on the cash basis
        tax line, while its balance is prorated by the reconciled percentage.
        As this module reports the tax base from this line (the base lines of
        the cash basis entry are not used), a partial payment ends up with a
        base that does not match the cleared tax, i.e. base 700.00 with tax
        22.90 for a 7% tax. Prorate the base with the ratio of the tax.
        """
        vals = super()._prepare_cash_basis_tax_line_vals(
            tax_line, balance, amount_currency
        )
        currency = tax_line.company_currency_id
        if not float_is_zero(tax_line.balance, precision_rounding=currency.rounding):
            ratio = balance / tax_line.balance
            vals["tax_base_amount"] = currency.round(tax_line.tax_base_amount * ratio)
        return vals

    def _get_move_type_cash_basis(self):
        return ["in_invoice", "entry"]

    def _update_state_cash_basis(self, moves):
        """Back state tax cash basis in bills and entry to draft
        not include net refund and payment. waiting clear tax later."""
        move_type = self._get_move_type_cash_basis()
        for move in moves:
            if move.tax_cash_basis_origin_move_id.move_type in move_type:
                move.mapped("line_ids").remove_move_reconcile()
                move.write({"state": "draft", "is_move_sent": False})

    def _create_tax_cash_basis_moves(self):
        """This method is called from the move lines that
        create cash basis entry. We want to use the same payment_id when
        create account.move.tax.invoice"""
        move_lines = self.debit_move_id | self.credit_move_id
        payment = move_lines.mapped("payment_id")
        if len(payment) == 1:
            self = self.with_context(payment_id=payment.id)
        moves = super()._create_tax_cash_basis_moves()
        # EXPERIMENT: remove income / expense account move lines
        ml_groups = self.env["account.move.line"].read_group(
            domain=[("move_id", "in", moves.ids)],
            fields=[
                "move_id",
                "account_id",
                "debit",
                "credit",
            ],
            groupby=[
                "move_id",
                "account_id",
            ],
            lazy=False,
        )
        del_ml_groups = list(filter(lambda l: l["debit"] == l["credit"], ml_groups))
        account_ids = [g.get("account_id")[0] for g in del_ml_groups]
        # Not include taxes (0%) and not reconciled
        del_move_lines = moves.mapped("line_ids").filtered(
            lambda line: line.account_id.id in account_ids
            and not line.tax_line_id
            and not line.reconciled
        )
        if del_move_lines:
            self.env.cr.execute(
                "DELETE FROM account_move_line WHERE id in %s",
                (tuple(del_move_lines.ids),),
            )
        net_invoice_refund = self.env.context.get("net_invoice_refund")
        net_invoice_payment = self.env.context.get("net_invoice_payment")
        if not net_invoice_refund or net_invoice_payment:
            self._update_state_cash_basis(moves)
        # --
        return moves
