import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-open-synergy-opnsynid-social",
    description="Meta package for open-synergy-opnsynid-social Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-ssi_mail',
        'odoo14-addon-ssi_mail_optional_related_attachment',
        'odoo14-addon-ssi_mail_telegram',
        'odoo14-addon-ssi_telegram',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
