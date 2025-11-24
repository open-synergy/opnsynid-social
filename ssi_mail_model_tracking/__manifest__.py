{
    "name": "SSI Mail Model Tracking",
    "summary": "Track email opens per model using a toggle on ir.model.",
    "version": "14.0.1.0.0",
    "category": "Tools",
    "author": "PT. Simetri Sinergi Indonesia",
    "website": "https://simetri-sinergi.id",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
    ],
    "data": [
        "views/ir_model.xml",
        "views/mail_mail.xml",
    ],
    "installable": True,
    "application": False,
}
