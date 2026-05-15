import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo11-addons-open-synergy-opnsynid-social",
    description="Meta package for open-synergy-opnsynid-social Odoo addons",
    version=version,
    install_requires=[
        'odoo11-addon-mail_sendgrid',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 11.0',
    ]
)
