import logging
import uuid

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = "mail.mail"

    tracking_enabled = fields.Boolean(
        string="Tracking Enabled",
        help="Indicates that this mail includes an open-tracking pixel.",
        readonly=True,
    )
    tracking_token = fields.Char(
        string="Tracking Token",
        help="Unique token used by the tracking pixel URL.",
        readonly=True,
        index=True,
    )
    tracking_opened = fields.Boolean(
        string="Opened",
        help="Set to True when the tracking pixel for this email is loaded.",
        readonly=True,
    )
    tracking_opened_datetime = fields.Datetime(
        string="Opened On",
        help="Date and time when this email was first opened (via tracking pixel).",
        readonly=True,
    )
    tracking_open_count = fields.Integer(
        string="Open Count",
        help="Number of times the tracking pixel has been loaded.",
        readonly=True,
    )

    def _get_related_model_name(self):
        """Return the business model name associated with this mail.

        Priority:
        1. mail.mail.model (if present)
        2. mail.mail.mail_message_id.model (fallback)
        """
        self.ensure_one()
        if getattr(self, "model", False):
            return self.model
        if self.mail_message_id and self.mail_message_id.model:
            return self.mail_message_id.model
        return False

    def _should_enable_tracking_for_mail(self):
        """Decide whether tracking should be enabled for this mail.

        Logic:
        - Find related business model.
        - Check ir.model.track_email for that model.
        """
        self.ensure_one()
        model_name = self._get_related_model_name()
        if not model_name:
            return False

        ir_model_obj = self.env["ir.model"]
        try:
            return ir_model_obj.get_track_email_for_model(model_name)
        except Exception as exc:  # defensive: tracking must never break sending
            _logger.warning(
                "Failed to read track_email config for model %s: %s",
                model_name,
                exc,
            )
            return False

    def _get_tracking_pixel_url(self, token):
        """Build absolute URL for the tracking pixel based on web.base.url."""
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        if not base_url:
            # Fallback: relative URL (less ideal in emails, but still functional
            # in some clients). We do not block sending if base_url is missing.
            return "/mail/tracking/open/%s" % token
        if not base_url.endswith("/"):
            base_url += "/"
        return "%smail/tracking/open/%s" % (base_url, token)

    def _inject_tracking_pixel(self):
        """Inject tracking pixel into HTML body if not already present.

        This method:
        - Generates a token if missing,
        - Builds the pixel URL,
        - Appends an <img> tag to body_html,
        - Marks tracking_enabled = True.
        """
        for mail in self:
            if not mail.body_html:
                # We only handle HTML bodies; do not try to convert plain text.
                continue

            # Generate token once per mail
            if not mail.tracking_token:
                mail.tracking_token = uuid.uuid4().hex

            pixel_url = mail._get_tracking_pixel_url(mail.tracking_token)

            # Avoid injecting the same pixel multiple times
            if pixel_url in mail.body_html:
                mail.tracking_enabled = True
                continue

            pixel_img = (
                '<img src="{url}" alt="" '
                'style="width:1px;height:1px;display:none;" />'
            ).format(url=pixel_url)

            # Simple strategy: append at the end of the HTML body
            mail.body_html = (mail.body_html or "") + pixel_img
            mail.tracking_enabled = True

    @api.model
    def _update_tracking_on_open(self, token):
        """Called by HTTP controller when tracking pixel is loaded.

        - Locate mail.mail by token,
        - Mark as opened (first time),
        - Increment open counter.
        """
        if not token:
            return

        mail = self.sudo().search(
            [
                ("tracking_token", "=", token),
            ],
            limit=1,
        )
        if not mail:
            return

        values = {
            "tracking_open_count": mail.tracking_open_count + 1,
        }
        if not mail.tracking_opened:
            values.update(
                {
                    "tracking_opened": True,
                    "tracking_opened_datetime": fields.Datetime.now(),
                }
            )
        mail.write(values)

    def send(self, auto_commit=False, raise_exception=False):
        """Override send() to inject tracking pixel when enabled per model.

        - For each mail, check ir.model.track_email on its business model.
        - If True, inject tracking pixel into body_html.
        - Then call super().send().
        """
        for mail in self:
            try:
                if mail._should_enable_tracking_for_mail():
                    mail._inject_tracking_pixel()
            except Exception as exc:
                # Tracking must never block email delivery.
                _logger.warning(
                    "Failed to inject tracking pixel for mail ID %s: %s",
                    mail.id,
                    exc,
                )
        return super().send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
        )
