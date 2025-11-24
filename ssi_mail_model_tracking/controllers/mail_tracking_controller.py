import base64

from odoo import http
from odoo.http import request


class MailTrackingController(http.Controller):
    """HTTP endpoints for mail tracking.

    Currently provides:
    - /mail/tracking/open/<token>  -> 1x1 transparent GIF
    """

    # 1x1 transparent GIF (standard) in base64
    _TRANSPARENT_GIF_BASE64 = "R0lGODlhAQABAPAAAP///wAAACwAAAAAAQABAEACAkQBADs="

    @http.route(
        "/mail/tracking/open/<string:token>",
        type="http",
        auth="public",
        csrf=False,
    )
    def mail_tracking_open(self, token, **kwargs):
        """Route called when the tracking pixel is loaded.

        This route:
        - Updates tracking status on mail.mail,
        - Returns a transparent 1x1 GIF to the client.
        """
        # Update tracking status
        request.env["mail.mail"]._update_tracking_on_open(token)

        # Return transparent GIF
        image_bytes = base64.b64decode(self._TRANSPARENT_GIF_BASE64)
        headers = [
            ("Content-Type", "image/gif"),
            ("Content-Length", str(len(image_bytes))),
            # Cache controls to avoid over-caching in some proxies/clients
            ("Cache-Control", "no-cache, no-store, must-revalidate"),
            ("Pragma", "no-cache"),
            ("Expires", "0"),
        ]
        return request.make_response(image_bytes, headers=headers)
