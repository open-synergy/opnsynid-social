{
    "name": "SSI Telegram Notify",
    "version": "14.0.1.0.0",
    "summary": "Send Odoo thread notifications to users via Telegram Bot",
    "category": "Discuss",
    "author": "OpenSynID",
    "website": "https://simetri-sinergi.id",
    "license": "LGPL-3",
    "depends": ["base", "mail", "link_tracker"],
    "data": [
        "data/ir_config_parameter_data.xml",
        "views/res_users_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
