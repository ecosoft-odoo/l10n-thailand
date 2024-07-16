import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-l10n-thailand",
    description="Meta package for oca-l10n-thailand Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-currency_rate_update_TH_BOT>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_account_tax>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_account_tax_multi>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_account_tax_report>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_account_wht_cert_form>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_amount_to_text>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_bank_payment_export>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_base_location>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_fonts>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_mis_report>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_partner>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_promptpay>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_tier_department>=16.0dev,<16.1dev',
        'odoo-addon-l10n_th_tier_department_demo>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
