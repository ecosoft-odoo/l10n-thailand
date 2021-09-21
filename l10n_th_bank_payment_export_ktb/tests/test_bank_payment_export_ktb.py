# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import Form

from odoo.addons.l10n_th_bank_payment_export.tests.common import CommonBankPaymentExport


class TestBankPaymentExportKTB(CommonBankPaymentExport):
    def setUp(self):
        super().setUp()
        # paremeter config
        self.sender_name = self.env.ref(
            "l10n_th_bank_payment_export_ktb.export_payment_ktb_sender_name"
        )
        self.ktb_company = self.env.ref(
            "l10n_th_bank_payment_export_ktb.export_payment_ktb_company_id"
        )

    def test_01_config_parameter(self):
        bank_payment = self.bank_payment_export_model.create(
            {
                "name": "/",
                "bank": "KRTHTHBK",
            }
        )
        bank_payment.action_get_all_payments()
        self.assertEqual(len(bank_payment.export_line_ids), 2)
        # check config parameter
        self.assertFalse(bank_payment.config_ktb_company_id)
        self.assertFalse(bank_payment.config_ktb_sender_name)
        self.sender_name.value = "Test Sender Name"
        self.ktb_company.value = "Test KTB Company"
        bank_payment._compute_ktb_system_parameter()
        self.assertTrue(bank_payment.config_ktb_company_id)
        self.assertTrue(bank_payment.config_ktb_sender_name)

    def test_02_ktb_export(self):
        bank_payment = self.bank_payment_export_model.create(
            {
                "name": "/",
                "bank": "KRTHTHBK",
            }
        )
        bank_payment.action_get_all_payments()
        self.assertEqual(len(bank_payment.export_line_ids), 2)
        # Add recipient bank on line
        for line in bank_payment.export_line_ids:
            self.assertFalse(line.payment_id.is_export)
            if line.payment_partner_id == self.partner_2:
                # check default recipient bank
                self.assertTrue(line.payment_partner_bank_id)
            else:
                line.payment_partner_bank_id = self.partner1_bank_bnp.id
        # Criteria bank KTB is not selected
        with self.assertRaises(UserError):
            bank_payment.action_confirm()
        # Test onchange and effective date < today
        with self.assertRaises(UserError):
            with Form(bank_payment) as bp:
                bp.ktb_bank_type = "standard"
                bp.ktb_service_type_standard = "04"
                bp.ktb_effective_date = fields.Date.today() - timedelta(days=3)
        self.assertTrue(bank_payment.ktb_service_type_standard)
        self.assertFalse(bank_payment.ktb_service_type_direct)
        with Form(bank_payment) as bp:
            bp.ktb_bank_type = "direct"
            bp.ktb_service_type_direct = "14"
            bp.ktb_effective_date = fields.Date.today()
        self.assertFalse(bank_payment.ktb_service_type_standard)
        self.assertTrue(bank_payment.ktb_service_type_direct)
        # Type direct can't export payment to other bank
        with self.assertRaises(UserError):
            bank_payment.action_confirm()
        with Form(bank_payment) as bp:
            bp.ktb_bank_type = "standard"
            bp.ktb_service_type_standard = "04"
        bank_payment.action_confirm()

        # Export Excel
        xlsx_data = self.action_bank_export_excel(bank_payment)
        self.assertEqual(xlsx_data[1], "xlsx")
        # Export Text File
        text_list = bank_payment.action_export_text_file()
        self.assertEqual(bank_payment.state, "done")
        self.assertEqual(text_list["report_type"], "qweb-text")
        text_word = bank_payment._export_bank_payment_text_file()
        self.assertNotEqual(
            text_word,
            "Demo Text File. You can inherit function "
            "_generate_bank_payment_text() for customize your format.",
        )
        self.assertEqual(bank_payment.state, "done")