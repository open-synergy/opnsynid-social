import base64

from werkzeug.exceptions import BadRequest

from odoo import http, tools
from odoo.http import request
from odoo.tools import consteq


class MailTrackingController(http.Controller):
    """HTTP endpoints for mail open tracking.

    Meniru pola mass_mailing, tetapi untuk mail.trace (email biasa).
    """

    # 1x1 transparent GIF (standard) in base64
    _TRANSPARENT_GIF_BASE64 = (
        "R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
    )

    @http.route(
        "/mail/trace/<int:mail_id>/<string:token>/blank.gif",
        type="http",
        auth="public",
        csrf=False,
    )
    def mail_trace_open(self, mail_id, token, **kwargs):
        """Route dipanggil ketika tracking pixel di-load.

        - Validasi token dengan HMAC (ala mass_mailing).
        - Panggil mail.trace.set_opened() untuk mail_mail_id terkait.
        - Kembalikan GIF transparan 1x1.
        """
        expected = tools.hmac(
            request.env(su=True),
            "mail-trace-open",
            mail_id,
        )
        if not consteq(token, expected):
            # Token tidak valid -> jangan catat apa-apa
            raise BadRequest()

        # Update mail.trace dan sinkron ke mail.mail
        request.env["mail.trace"].sudo().set_opened(
            mail_mail_ids=[mail_id],
        )

        image_bytes = base64.b64decode(self._TRANSPARENT_GIF_BASE64)
        headers = [
            ("Content-Type", "image/gif"),
            ("Content-Length", str(len(image_bytes))),
            ("Cache-Control", "no-cache, no-store, must-revalidate"),
            ("Pragma", "no-cache"),
            ("Expires", "0"),
        ]
        return request.make_response(image_bytes, headers)
