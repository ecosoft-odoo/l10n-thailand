# Copyright 2019 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models

DEFAULT_DAY_FORMAT_WHT = "%d"
DEFAULT_MONTH_FORMAT_WHT = "%m"
DEFAULT_YEAR_FORMAT_WHT = "%Y"
INCOME_TAX_FORM = {"pnd1": "P01", "pnd3": "P03", "pnd53": "P53"}


class WithHoldingTaxReport(models.TransientModel):
    _name = "withholding.tax.report"
    _description = "Withholding Tax Report"

    income_tax_form = fields.Selection(
        selection=[("pnd1", "PND1"), ("pnd3", "PND3"), ("pnd53", "PND53")],
        string="Income Tax Form",
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        ondelete="cascade",
    )
    date_range_id = fields.Many2one(comodel_name="date.range", string="Date range")
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    show_cancel = fields.Boolean(string="Show cancelled")
    results = fields.Many2many(
        comodel_name="withholding.tax.cert.line",
        string="Results",
        compute="_compute_results",
        help="Use compute fields, so there is nothing store in database",
    )

    def _get_name_filter(self, title=False, firstname=False, lastname=False):
        return "{}|{}|{}".format(title or "", firstname or "", lastname or "")

    def find_information(self, partner_id, line):
        # PND53
        if line.wht_income_tax_form == "pnd53":
            name = "{}".format(
                partner_id.company_type == "person"
                and (partner_id.firstname or partner_id.lastname)
                or partner_id.name_company
            )
        # PND3, PND1
        else:
            name = (
                partner_id.company_type == "person"
                and self._get_name_filter(
                    title=partner_id.title.name,
                    firstname=partner_id.firstname,
                    lastname=partner_id.lastname,
                )
                or self._get_name_filter(firstname=partner_id.name_company)
            )
        return name

    def find_address(self, partner_id, line):
        if line.wht_income_tax_form == "pnd1":
            return ""
        return "|".join(
            [
                partner_id.street or "",
                partner_id.street2 or "",
                partner_id.city or "",
                partner_id.state_id.name or "",
                partner_id.zip or "",
            ]
        )

    def _create_text(self, docs):
        """Text File PND
        - PND1 :
            1. income code
            2. index
            3. vat
            4. title
            5. firstname
            6. lastname
            7. date
            8. type of income
            9. base amount
            10. wht amount
            11. tax payer

        - PND3 :
            1. index
            2. vat
            3. title
            4. firstname
            5. lastname
            6-10. Street, Street2, City, State ID, zip
            11. date
            12. type of income (description)
            13. wht percent
            14. base amount
            15. wht amount
            16. tax payer

        - PND53 :
            1. index
            2. vat
            3. name
            4-8. Street, Street2, City, State ID, zip
            9. date
            10. type of income (description)
            11. wht percent
            12. base amount
            13. wht amount
            14. tax payer
            15. tax branch
        """
        self.ensure_one()
        for obj in docs:
            text = ""
            for idx, line in enumerate(obj.results):
                income_code = (
                    line.wht_cert_income_code
                    and "{}|".format(line.wht_cert_income_code.code)
                    or ""
                )
                partner_id = line.cert_id.partner_id
                vat = partner_id.vat or ""
                type_income_desc = (
                    line.wht_income_tax_form != "pnd1"
                    and "{}|{}|".format(
                        line.wht_cert_income_desc, int(line.wht_percent)
                    )
                    or ""
                )
                name = obj.find_information(partner_id, line)
                address = obj.find_address(partner_id, line)
                tax_branch = (
                    line.wht_income_tax_form == "pnd53"
                    and "|{}".format(partner_id.branch or "")
                    or ""
                )
                text += (
                    "{income_code}{index}|{vat}|{name}|{address}{date}|"
                    "{type_income_desc}{base_amount}|{wht_amount}|{tax_payer}"
                    "{tax_branch}\n".format(
                        income_code=income_code,  # for pnd1 only
                        index=idx + 1,
                        vat=vat,
                        name=name,
                        address=address
                        and "{}|".format(address)
                        or "",  # pnd3, 53 (optional)
                        date=self.format_date_dmy(line.cert_id.date),
                        type_income_desc=type_income_desc,
                        base_amount="{:,.2f}".format(line.base) or 0.00,
                        wht_amount="{:,.2f}".format(line.amount) or 0.00,
                        tax_payer=self._convert_tax_payer(line.cert_id.tax_payer),
                        tax_branch=tax_branch,
                    )
                )
        return text

    def _convert_tax_payer(self, tax_payer):
        if tax_payer == "withholding":
            return 1
        return 3  # paid one time

    def format_date_dmy(self, date=None, format_date=None):
        if not date:
            date = fields.Date.context_today()
        year_thai = int(date.strftime(DEFAULT_YEAR_FORMAT_WHT)) + 543
        date_format = date.strftime(
            "{}{}{}".format(DEFAULT_DAY_FORMAT_WHT, DEFAULT_MONTH_FORMAT_WHT, year_thai)
        )
        return date_format

    def format_date(self, date=None):
        if not date:
            # date month before
            date = self.date_from
        year_thai = int(date.strftime(DEFAULT_YEAR_FORMAT_WHT)) + 543
        month = date.strftime(DEFAULT_MONTH_FORMAT_WHT)
        date_format = "{}{}".format(year_thai, month)
        return date_format

    def _get_report_base_filename(self):
        self.ensure_one()
        pnd = INCOME_TAX_FORM[self.income_tax_form]
        date_format = self.format_date()
        return "WHT-{}-{}".format(pnd, date_format)

    def print_report(self, report_type="qweb"):
        self.ensure_one()
        if report_type == "xlsx":
            report_name = "withholding.tax.report.xlsx"
        elif report_type == "qweb-text":
            report_name = "l10n_th_account_tax_report.report_withholding_tax_text"
        else:
            report_name = "l10n_th_account_tax_report.report_withholding_tax_qweb"
        context = dict(self.env.context)
        action = self.env["ir.actions.report"].search(
            [("report_name", "=", report_name), ("report_type", "=", report_type)],
            limit=1,
        )
        return action.with_context(context).report_action(self, config=False)

    def _get_html(self):
        result = {}
        rcontext = {}
        context = dict(self.env.context)
        report = self.browse(context.get("active_id"))
        if report:
            rcontext["o"] = report
            result["html"] = self.env.ref(
                "l10n_th_account_tax_report.report_withholding_tax_html"
            )._render(rcontext)
        return result

    @api.model
    def get_html(self, given_context=None):
        return self.with_context(given_context)._get_html()

    @api.onchange("date_range_id")
    def _onchange_date_range_id(self):
        self.date_from = self.date_range_id.date_start
        self.date_to = self.date_range_id.date_end

    def _compute_results(self):
        self.ensure_one()
        Result = self.env["withholding.tax.cert.line"]
        # fields required
        domain = [
            ("cert_id.income_tax_form", "=", self.income_tax_form),
            ("cert_id.date", ">=", self.date_from),
            ("cert_id.date", "<=", self.date_to),
            ("cert_id.company_partner_id", "=", self.company_id.partner_id.id),
            ("cert_id.state", "!=", "draft"),
        ]
        if not self.show_cancel:
            domain += [("cert_id.state", "!=", "cancel")]
        self.results = Result.sudo().search(domain)