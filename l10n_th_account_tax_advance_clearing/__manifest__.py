# Copyright 2020 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

{
    "name": "Thai Localization - Advance Clearing Withholding Tax",
    "version": "14.0.1.0.0",
    "author": "Ecosoft,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/l10n-thailand",
    "category": "Localization / Accounting",
    "depends": ["l10n_th_account_tax_expense", "hr_expense_advance_clearing"],
    "data": [
        "views/hr_expense_view.xml",
    ],
    "installable": True,
    "auto_install": True,
    "development_status": "Beta",
    "maintainers": ["kittiu"],
}