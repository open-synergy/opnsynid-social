{
    "name": "SSI Mail Model Tracking",
    "summary": "Track email opens per model using a toggle on ir.model.",
    "version": "14.0.1.1.0",
    "category": "Tools",
    "author": "PT. Simetri Sinergi Indonesia",
    "website": "https://simetri-sinergi.id",
    "license": "AGPL-3",
    "depends": [
        "base",
        "mail",
    ],
    "data": [
        "security/ir_model_access/mail_trace.xml",
        "views/ir_model.xml",
        "views/mail_mail.xml",
        "views/mail_template.xml",
        "views/mail_trace.xml",
    ],
    "installable": True,
    "application": False,
}
