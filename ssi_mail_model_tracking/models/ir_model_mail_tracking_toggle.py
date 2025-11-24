from odoo import api, fields, models


class IrModel(models.Model):
    _inherit = "ir.model"

    track_email = fields.Boolean(
        string="Track Emails",
        help=(
            "If enabled, outgoing emails related to this model "
            "will include an open-tracking pixel to detect when they are opened."
        ),
    )

    @api.model
    def get_track_email_for_model(self, model_name):
        """Helper to read the toggle for a given model name.

        Using sudo() so that tracking still works even if the user
        does not have access to ir.model.
        """
        if not model_name:
            return False
        ir_model = self.sudo().search(
            [
                ("model", "=", model_name),
            ],
            limit=1,
        )
        return bool(ir_model and ir_model.track_email)
