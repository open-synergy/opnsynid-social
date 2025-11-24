from odoo import api, fields, models


class MailTrace(models.Model):
    _name = "mail.trace"
    _description = "Mail Trace"
    _order = "sent desc, id desc"

    mail_mail_id = fields.Many2one(
        comodel_name="mail.mail",
        string="Mail",
        required=True,
        ondelete="cascade",
        index=True,
    )
    email = fields.Char(
        string="Email",
        help="Recipient email address associated with this trace.",
    )
    state = fields.Selection(
        selection=[
            ("sent", "Sent"),
            ("opened", "Opened"),
            ("bounced", "Bounced"),
            ("ignored", "Ignored"),
        ],
        string="State",
        default="sent",
        index=True,
    )
    message_id = fields.Char(
        string="Message-ID",
        help="Message-ID used by the outgoing SMTP message, if any.",
    )
    scheduled = fields.Datetime(
        string="Scheduled",
        help="Date when this mail was scheduled to be sent.",
    )
    sent = fields.Datetime(
        string="Sent",
        help="Date when this mail was considered sent.",
    )
    opened = fields.Datetime(
        string="Opened",
        help="Date when this mail was first opened (tracking pixel loaded).",
    )
    clicked = fields.Datetime(
        string="Clicked",
        help="Reserved for future use (click tracking).",
    )
    replied = fields.Datetime(
        string="Replied",
        help="Reserved for future use (reply tracking).",
    )
    bounced = fields.Datetime(
        string="Bounced",
        help="Reserved for future use (bounce tracking).",
    )
    ignored = fields.Datetime(
        string="Ignored",
        help="Reserved for future use (ignored tracking).",
    )
    exception = fields.Char(
        string="Exception",
        help="Optional technical information when sending fails.",
    )

    # -------------------------------------------------------------------------
    # Helpers mirip mailing.trace
    # -------------------------------------------------------------------------

    @api.model
    def _get_records(self, mail_mail_ids=None, extra_domain=None):
        domain = []
        if mail_mail_ids:
            domain.append(("mail_mail_id", "in", mail_mail_ids))
        if extra_domain:
            domain += list(extra_domain)
        return self.search(domain)

    def set_opened(self, mail_mail_ids=None):
        """Set opened on traces + sinkron ke mail.mail tracking_*."""
        traces = self._get_records(
            mail_mail_ids=mail_mail_ids,
            extra_domain=[("opened", "=", False)],
        )
        if not traces:
            return traces

        now = fields.Datetime.now()
        traces.write(
            {
                "opened": now,
                "state": "opened",
            }
        )

        # Sinkron ke mail.mail (field tracking_* yang sudah ada di modul lama)
        mails = traces.mapped("mail_mail_id")
        for mail in mails:
            values = {
                "tracking_open_count": (mail.tracking_open_count or 0) + 1,
            }
            if not mail.tracking_opened:
                values.update(
                    {
                        "tracking_opened": True,
                        "tracking_opened_datetime": now,
                    }
                )
            mail.sudo().write(values)

        return traces
