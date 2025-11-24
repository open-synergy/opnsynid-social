import logging

import werkzeug.urls

from odoo import fields, models, tools

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = "mail.mail"

    # Field tracking dari versi sebelumnya tetap dipertahankan
    tracking_enabled = fields.Boolean(
        string="Tracking Enabled",
        help="Indicates that this mail includes an open-tracking pixel.",
        readonly=True,
    )
    tracking_token = fields.Char(
        string="Tracking Token",
        help=(
            "Legacy token used by the tracking pixel URL. "
            "Kept for compatibility; new implementation uses HMAC on ID."
        ),
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
    tracking_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Tracking Template",
        readonly=True,
        help="Email template that determined tracking behavior for this mail, "
        "when applicable.",
    )
    tracking_template_mode = fields.Selection(
        selection=[
            ("model", "Use Model Setting"),
            ("force_on", "Always Track (override model)"),
            ("force_off", "Never Track (override model)"),
        ],
        string="Template Tracking Mode",
        readonly=True,
        help="Effective tracking mode decided at template level for this mail.",
    )

    # -------------------------------------------------------------------------
    # Keputusan: perlu tracking atau tidak (kombinasi model + template)
    # -------------------------------------------------------------------------

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

        Priority:
        1. Template override (tracking_template_mode):
           - force_on  -> always True
           - force_off -> always False
        2. Model setting (ir.model.track_email) when template mode is 'model'
           or not set.
        """
        self.ensure_one()

        # 1) Per-template override
        template_mode = self.tracking_template_mode
        if template_mode == "force_on":
            return True
        if template_mode == "force_off":
            return False

        # 2) Fallback ke per-model toggle
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

    # -------------------------------------------------------------------------
    # URL tracking ala mass_mailing (HMAC + /mail/trace/<id>/<token>/blank.gif)
    # -------------------------------------------------------------------------

    def _get_tracking_pixel_url(self):
        """Build absolute URL for the tracking pixel based on web.base.url.

        Menggunakan HMAC pada ID, mirip mass_mailing untuk menghindari
        pemalsuan token.
        """
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")

        # Salt khusus modul ini, jangan sama dengan mass_mailing
        token = tools.hmac(
            self.env(su=True),
            "mail-trace-open",
            self.id,
        )

        path = "mail/trace/%s/%s/blank.gif" % (self.id, token)
        if base_url:
            if not base_url.endswith("/"):
                base_url += "/"
            return werkzeug.urls.url_join(base_url, path)
        # Fallback relatif (sebagian client mungkin tidak suka, tapi aman)
        return "/" + path

    def _ensure_mail_trace(self):
        """Pastikan ada record mail.trace untuk mail ini.

        Sederhana: satu trace per mail.mail. Status awal = 'sent'.
        """
        self.ensure_one()
        Trace = self.env["mail.trace"].sudo()
        trace = Trace.search(
            [
                ("mail_mail_id", "=", self.id),
            ],
            limit=1,
        )
        if trace:
            return trace

        # Ambil alamat email utama dari mail.mail
        email = self.email_to or False
        if not email and self.partner_ids:
            email = self.partner_ids[0].email or False

        now = fields.Datetime.now()
        trace_vals = {
            "mail_mail_id": self.id,
            "email": email,
            "state": "sent",
            "scheduled": now,
            "sent": now,
            "message_id": self.message_id,
        }
        return Trace.create(trace_vals)

    # -------------------------------------------------------------------------
    # Override _send_prepare_body (ala mass_mailing) untuk inject pixel
    # -------------------------------------------------------------------------

    def _send_prepare_body(self):
        """Inject tracking pixel ala mass_mailing untuk email biasa.

        - Dipanggil per record oleh mail.mail._send().
        - Tidak mengganggu mass_mailing (yang memakai mailing_id sendiri).
        """
        self.ensure_one()
        body = super()._send_prepare_body()

        # Jangan ganggu email mass_mailing; mereka punya tracking sendiri
        if getattr(self, "mailing_id", False):
            return body

        try:
            if body and self._should_enable_tracking_for_mail():
                pixel_url = self._get_tracking_pixel_url()
                # Mirip mass_mailing: sisipkan img ke HTML
                body = tools.append_content_to_html(
                    body,
                    '<img src="%s" alt="" style="width:1px;height:1px;display:none;"/>'  # noqa: E501
                    % pixel_url,
                    plaintext=False,
                )
                self.tracking_enabled = True
                # Buat trace untuk email ini
                self._ensure_mail_trace()
        except Exception as exc:
            # Tracking tidak boleh menghalangi pengiriman email
            _logger.warning(
                "Failed to inject tracking pixel for mail ID %s: %s",
                self.id,
                exc,
            )
        return body
