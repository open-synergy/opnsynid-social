from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    track_email_mode = fields.Selection(
        selection=[
            ("model", "Use Model Setting"),
            ("force_on", "Always Track (override model)"),
            ("force_off", "Never Track (override model)"),
        ],
        string="Email Tracking",
        default="model",
        help=(
            "Control open-tracking for emails generated from this template.\n"
            "- Use Model Setting: follow the Track Emails flag on the related model.\n"
            "- Always Track: force open-tracking on, regardless of the model flag.\n"
            "- Never Track: disable open-tracking, regardless of the model flag."
        ),
    )

    def send_mail(
        self,
        res_id,
        force_send=False,
        raise_exception=False,
        email_values=None,
        notif_layout=False,
    ):
        """Override send_mail to record template tracking mode on mail.mail.

        We only override tracking when the template is explicitly set to
        Always Track or Never Track. When 'Use Model Setting' is selected,
        tracking is decided purely by the related model.
        """
        self.ensure_one()
        mail_id = super().send_mail(
            res_id,
            force_send=force_send,
            raise_exception=raise_exception,
            email_values=email_values,
            notif_layout=notif_layout,
        )
        if not mail_id:
            return mail_id

        if self.track_email_mode and self.track_email_mode != "model":
            mail = self.env["mail.mail"].browse(mail_id)
            # Use sudo so tracking info is written even if caller has limited rights
            mail.sudo().write(
                {
                    "tracking_template_id": self.id,
                    "tracking_template_mode": self.track_email_mode,
                }
            )
        return mail_id
