# Copyright 2020 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import Form, TransactionCase


class TestAccountTaxMulti(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payment_model = cls.env["account.payment"]
        cls.partner_1 = cls.env.ref("base.res_partner_12")
        cls.product_1 = cls.env.ref("product.product_product_4")
        cls.current_asset = cls.env.ref("account.data_account_type_current_assets")
        cls.expenses = cls.env.ref("account.data_account_type_expenses")
        cls.revenue = cls.env.ref("account.data_account_type_revenue")
        cls.view_id = "account.view_account_payment_register_form"
        cls.account_move = cls.env["account.move"]
        cls.payment_register = cls.env["account.payment.register"]
        cls.account_account = cls.env["account.account"]
        cls.account_journal = cls.env["account.journal"]
        cls.account_wht = cls.env["account.withholding.tax"]
        cls.wht_account = cls.account_account.create(
            {
                "code": "X152000",
                "name": "Withholding Tax Account Test",
                "user_type_id": cls.current_asset.id,
                "wht_account": True,
            }
        )
        cls.wht_3 = cls.account_wht.create(
            {
                "name": "Withholding Tax 3%",
                "account_id": cls.wht_account.id,
                "amount": 3,
            }
        )
        cls.wht_5 = cls.account_wht.create(
            {
                "name": "Withholding Tax 5%",
                "account_id": cls.wht_account.id,
                "amount": 5,
            }
        )
        cls.expense_account = cls.account_account.search(
            [
                ("user_type_id", "=", cls.expenses.id),
                ("company_id", "=", cls.env.user.company_id.id),
            ],
            limit=1,
        )
        cls.sale_account = cls.account_account.search(
            [
                ("user_type_id", "=", cls.revenue.id),
                ("company_id", "=", cls.env.user.company_id.id),
            ],
            limit=1,
        )
        cls.expenses_journal = cls.account_journal.search(
            [
                ("type", "=", "purchase"),
                ("company_id", "=", cls.env.user.company_id.id),
            ],
            limit=1,
        )
        cls.sales_journal = cls.account_journal.search(
            [("type", "=", "sale"), ("company_id", "=", cls.env.user.company_id.id)],
            limit=1,
        )
        # Undue VAT, to test the tax base amount on partial payment
        cls.journal_undue = cls.account_journal.create(
            {"name": "Undue Journal", "type": "general", "code": "UNDUE"}
        )
        cls.env.user.company_id.write(
            {
                "tax_exigibility": True,
                "tax_cash_basis_journal_id": cls.journal_undue.id,
            }
        )
        cls.undue_input_vat_acct = cls.account_account.create(
            {
                "name": "DV7",
                "code": "DV7",
                "user_type_id": cls.current_asset.id,
            }
        )
        cls.input_vat_acct = cls.account_account.create(
            {
                "name": "V7",
                "code": "V7",
                "user_type_id": cls.current_asset.id,
            }
        )
        cls.undue_input_vat = cls.env["account.tax"].create(
            {
                "name": "DV7",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 7.0,
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": cls.undue_input_vat_acct.id,
                "invoice_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100.0, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100.0,
                            "repartition_type": "tax",
                            "account_id": cls.input_vat_acct.id,
                        },
                    ),
                ],
            }
        )

    def _create_invoice(
        self,
        partner_id,
        journal_id,
        invoice_type,
        line_account_id,
        price_unit,
        product_id=False,
        multi=False,
        tax_ids=False,
    ):
        invoice_dict = {
            "name": "Test Supplier Invoice WHT",
            "partner_id": partner_id,
            "journal_id": journal_id,
            "move_type": invoice_type,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": product_id,
                        "quantity": 1.0,
                        "account_id": line_account_id,
                        "name": "Advice1",
                        "price_unit": price_unit or 0.0,
                        "tax_ids": [(6, 0, tax_ids or [])],
                    },
                )
            ],
        }
        if multi:
            invoice_dict["invoice_line_ids"].append(
                (
                    0,
                    0,
                    {
                        "product_id": product_id,
                        "quantity": 1.0,
                        "account_id": line_account_id,
                        "name": "Advice2",
                        "price_unit": price_unit or 0.0,
                        "tax_ids": [(6, 0, tax_ids or [])],
                    },
                )
            )
        invoice = self.account_move.create(invoice_dict)
        return invoice

    def _config_product_withholding_tax(
        self, product_id, account, customer=False, vendor=False
    ):
        if customer:
            product_id.write({"wht_tax_id": account})
        if vendor:
            product_id.write({"supplier_wht_tax_id": account})
        return product_id

    def test_01_create_payment_withholding_tax(self):
        price_unit = 100.0
        with self.assertRaises(ValidationError):
            self.wht_3.write({"account_id": self.expense_account.id})
        invoice = self._create_invoice(
            self.partner_1.id,
            self.expenses_journal.id,
            "in_invoice",
            self.expense_account.id,
            price_unit,
        )
        invoice2 = self._create_invoice(
            self.partner_1.id,
            self.expenses_journal.id,
            "in_invoice",
            self.expense_account.id,
            price_unit,
        )
        self.assertFalse(invoice.invoice_line_ids.wht_tax_id)
        invoice.invoice_line_ids.write({"wht_tax_id": self.wht_3.id})
        self.assertTrue(invoice.invoice_line_ids.wht_tax_id)
        invoice.action_post()
        # Test multi invoice and withholding tax in line
        ctx = {
            "active_ids": [invoice.id, invoice2.id],
            "active_model": "account.move",
        }
        with self.assertRaises(UserError):
            f = Form(
                self.payment_register.with_context(**ctx),
                view=self.view_id,
            )
        # Payment by writeoff with withholding tax account
        ctx = {
            "active_ids": [invoice.id],
            "active_id": invoice.id,
            "active_model": "account.move",
        }
        f = Form(self.payment_register.with_context(**ctx), view=self.view_id)
        register_payment = f.save()
        self.assertEqual(register_payment.payment_difference_handling, "reconcile")
        self.assertEqual(
            register_payment.writeoff_account_id,
            invoice.invoice_line_ids.wht_tax_id.account_id,
        )
        self.assertEqual(register_payment.payment_difference, price_unit * 0.03)
        self.assertEqual(register_payment.writeoff_label, "Withholding Tax 3%")
        payment_id = register_payment._create_payments()
        payment = self.payment_model.browse(payment_id.id)
        self.assertEqual(payment.state, "posted")
        self.assertEqual(payment.amount, price_unit * 0.97)

    def test_02_create_payment_multi_withholding_tax_multi_line(self):
        """Create payment with 2 withholding tax on 2 line"""
        price_unit = 100.0
        invoice = self._create_invoice(
            self.partner_1.id,
            self.expenses_journal.id,
            "in_invoice",
            self.expense_account.id,
            price_unit,
            multi=True,
        )
        self.assertFalse(invoice.invoice_line_ids.wht_tax_id)
        invoice.invoice_line_ids[0].wht_tax_id = self.wht_3
        invoice.invoice_line_ids[1].wht_tax_id = self.wht_5
        self.assertTrue(invoice.invoice_line_ids.wht_tax_id)
        invoice.action_post()
        # Payment by writeoff with withholding tax account
        ctx = {
            "active_ids": [invoice.id],
            "active_id": invoice.id,
            "active_model": "account.move",
        }
        f = Form(self.payment_register.with_context(**ctx), view=self.view_id)
        register_payment = f.save()
        self.assertEqual(
            register_payment.payment_difference_handling,
            "reconcile_multi_deduct",
        )
        self.assertTrue(register_payment.deduction_ids)
        # Change wht_3 to wht_5
        with self.assertRaises(UserError):
            with Form(register_payment) as f:
                with f.deduction_ids.edit(0) as line:
                    line.wht_tax_id = self.wht_5
        # amount must reducted to 190
        with Form(register_payment) as f:
            with f.deduction_ids.edit(0) as line:
                line.wht_tax_id = self.wht_5
            f.amount = 190
        payment = register_payment._create_payments()
        self.assertEqual(payment.state, "posted")
        self.assertEqual(
            payment.amount,
            (price_unit * 2) - sum(register_payment.deduction_ids.mapped("amount")),
        )

    def test_03_create_payment_one_withholding_tax_multi_line(self):
        """Create payment with 1 withholding tax on 2 line"""
        price_unit = 100.0
        invoice = self._create_invoice(
            self.partner_1.id,
            self.expenses_journal.id,
            "in_invoice",
            self.expense_account.id,
            price_unit,
            multi=True,
        )
        self.assertFalse(invoice.invoice_line_ids.wht_tax_id)
        invoice.invoice_line_ids[0].wht_tax_id = self.wht_3
        invoice.invoice_line_ids[1].wht_tax_id = self.wht_3
        self.assertTrue(invoice.invoice_line_ids.mapped("wht_tax_id"))
        invoice.action_post()
        ctx = {
            "active_ids": [invoice.id],
            "active_id": invoice.id,
            "active_model": "account.move",
        }
        f = Form(self.payment_register.with_context(**ctx), view=self.view_id)
        register_payment = f.save()
        self.assertEqual(
            register_payment.payment_difference_handling,
            "reconcile",
        )
        self.assertFalse(register_payment.deduction_ids)
        payment_id = register_payment._create_payments()
        payment = self.payment_model.browse(payment_id.id)
        self.assertEqual(payment.state, "posted")
        self.assertEqual(
            payment.amount,
            invoice.amount_total - invoice.amount_untaxed * self.wht_3.amount / 100,
        )

    def test_04_create_payment_multi_withholding_keep_open(self):
        """Create payment with 2 withholding tax on 2 line and keep open 1"""
        price_unit = 100.0
        invoice = self._create_invoice(
            self.partner_1.id,
            self.expenses_journal.id,
            "in_invoice",
            self.expense_account.id,
            price_unit,
            multi=True,
        )
        self.assertFalse(invoice.invoice_line_ids.wht_tax_id)
        invoice.invoice_line_ids[0].wht_tax_id = self.wht_3
        invoice.invoice_line_ids[1].wht_tax_id = self.wht_5
        self.assertTrue(invoice.invoice_line_ids.mapped("wht_tax_id"))
        invoice.action_post()
        # Payment by writeoff with withholding tax account
        ctx = {
            "active_ids": [invoice.id],
            "active_id": invoice.id,
            "active_model": "account.move",
        }
        f = Form(self.payment_register.with_context(**ctx), view=self.view_id)
        register_payment = f.save()
        self.assertEqual(
            register_payment.payment_difference_handling,
            "reconcile_multi_deduct",
        )
        self.assertTrue(register_payment.deduction_ids)
        # Keep 3% and deduct 5%
        deduct_3 = register_payment.deduction_ids.filtered(
            lambda l: l.wht_tax_id == self.wht_3
        )
        with Form(deduct_3) as deduct:
            deduct.open = True
        self.assertFalse(deduct.wht_tax_id)
        payment_id = register_payment._create_payments()
        payment = self.payment_model.browse(payment_id.id)
        self.assertEqual(len(payment.line_ids.mapped("move_id")), 1)
        # cehck reconcile
        self.assertEqual(invoice.payment_state, "partial")
        self.assertFalse(payment.line_ids.mapped("full_reconcile_id"))
        # paid residual, it should be reconcile
        with Form(self.payment_register.with_context(**ctx), view=self.view_id) as f:
            f.amount = 0
            f.deduction_ids.remove(index=1)
        register_payment = f.save()
        register_payment.action_create_payments()
        self.assertEqual(invoice.payment_state, "paid")
        self.assertTrue(payment.line_ids.mapped("full_reconcile_id"))

    def test_05_undue_vat_tax_base_on_partial_payment(self):
        """Undue VAT, multi deduct and keep open 1 deduction.

        The tax base of the tax invoice must be prorated with the same ratio
        as the cleared tax, not the full base amount of the bill.
        """
        price_unit = 100.0
        invoice = self._create_invoice(
            self.partner_1.id,
            self.expenses_journal.id,
            "in_invoice",
            self.expense_account.id,
            price_unit,
            multi=True,
            tax_ids=self.undue_input_vat.ids,
        )
        invoice.invoice_line_ids[0].wht_tax_id = self.wht_3
        invoice.invoice_line_ids[1].wht_tax_id = self.wht_5
        invoice.action_post()
        base_amount = sum(invoice.invoice_line_ids.mapped("price_subtotal"))
        self.assertEqual(base_amount, 200.0)
        ctx = {
            "active_ids": [invoice.id],
            "active_id": invoice.id,
            "active_model": "account.move",
        }
        f = Form(self.payment_register.with_context(**ctx), view=self.view_id)
        register_payment = f.save()
        self.assertEqual(
            register_payment.payment_difference_handling,
            "reconcile_multi_deduct",
        )
        # Keep 3% open, so the bill is not fully paid
        deduct_3 = register_payment.deduction_ids.filtered(
            lambda l: l.wht_tax_id == self.wht_3
        )
        with Form(deduct_3) as deduct:
            deduct.open = True
        payment_id = register_payment._create_payments()
        payment = self.payment_model.browse(payment_id.id)
        self.assertEqual(invoice.payment_state, "partial")
        tax_invoices = payment.tax_invoice_ids
        self.assertTrue(tax_invoices)
        tax_base = sum(tax_invoices.mapped("tax_base_amount"))
        tax_amount = sum(tax_invoices.mapped("balance"))
        # Partially cleared, base can't be the full base amount of the bill
        self.assertLess(tax_base, base_amount)
        # Base and tax are consistent with the tax rate
        self.assertAlmostEqual(
            tax_amount, tax_base * self.undue_input_vat.amount / 100, places=2
        )

    # TODO: test for PIT cases
