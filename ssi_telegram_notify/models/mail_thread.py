import logging
import re

from odoo import models

_logger = logging.getLogger(__name__)


def _strip_html(raw_html):
    """Return plain text from an HTML string without footnote-style link conversion."""
    import html as html_lib

    text = re.sub(r"<[^>]+>", " ", raw_html or "")
    text = html_lib.unescape(text)
    return re.sub(
        r" {2,}|\n{3,}", lambda m: "\n\n" if "\n" in m.group() else " ", text
    ).strip()


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    # ------------------------------------------------------------------
    # Override
    # ------------------------------------------------------------------

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        """Override to forward notifications to Telegram after the standard
        Odoo notification pipeline has completed."""
        result = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)
        try:
            self._send_telegram_notifications(message, msg_vals=msg_vals)
        except Exception as exc:
            # Never let Telegram errors bubble up and roll back the transaction.
            _logger.exception(
                "Unexpected error while dispatching Telegram notifications: %s", exc
            )
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _send_telegram_notifications(self, message, msg_vals=False):
        """Forward *message* to every recipient that has Telegram notify enabled.

        :param message: ``mail.message`` record that was just posted.
        :param msg_vals: optional dict of pre-computed message values passed by
                         the caller (same contract as ``_notify_thread``).
        """
        IrConfig = self.env["ir.config_parameter"].sudo()
        bot_token = IrConfig.get_param("telegram.bot.token", "").strip()
        if not bot_token:
            return

        # ---- Build plain-text body ----------------------------------------
        body_html = (msg_vals.get("body") if msg_vals else None) or message.body or ""
        body_text = _strip_html(body_html)
        if not body_text:
            return

        # ---- Build thread link --------------------------------------------
        base_url = IrConfig.get_param("web.base.url", "").rstrip("/")
        # mail.message uses `model` + `res_id` (not `res_model`)
        res_model = (
            (msg_vals or {}).get("res_model")
            or (msg_vals or {}).get("model")
            or message.model
        )
        res_id = (msg_vals or {}).get("res_id") or message.res_id
        thread_link = ""
        if base_url and res_model and res_id:
            long_url = "{}/mail/view?model={}&res_id={}".format(
                base_url, res_model, res_id
            )
            # Shorten the URL via link.tracker so Telegram auto-links it
            thread_link = self._get_short_url(long_url)

        # ---- Compose final text -------------------------------------------
        full_text = body_text

        # ---- Collect partner recipients ------------------------------------
        # msg_vals may carry partner_ids as a list of IDs (command tuples or
        # plain ints).  We normalise to a plain list of integer IDs.
        raw_partner_ids = []
        if msg_vals and msg_vals.get("partner_ids"):
            for item in msg_vals["partner_ids"]:
                if isinstance(item, (list, tuple)):
                    # ORM command format, e.g. (4, id, 0)
                    raw_partner_ids.append(item[1])
                elif isinstance(item, int):
                    raw_partner_ids.append(item)

        partners = self.env["res.partner"].browse(raw_partner_ids)
        # Also include partners already linked on the message record itself.
        partners |= message.partner_ids

        if not partners:
            return

        # ---- Dispatch messages --------------------------------------------
        for partner in partners:
            telegram_users = partner.user_ids.filtered(
                lambda u: u.notify_via_telegram and u.telegram_chat_id
            )
            for user in telegram_users:
                self._dispatch_telegram_message(
                    bot_token=bot_token,
                    chat_id=user.telegram_chat_id,
                    text=full_text,
                    thread_link=thread_link,
                )

    def _get_short_url(self, long_url):
        """Create (or reuse) a link.tracker record and return the short URL.

        Falls back to the original *long_url* if the link_tracker module is
        not installed or an error occurs.
        """
        try:
            LinkTracker = self.env["link.tracker"].sudo()
            tracker = LinkTracker.create({"url": long_url})
            return tracker.short_url or long_url
        except Exception:
            _logger.debug(
                "link.tracker unavailable, falling back to long URL", exc_info=True
            )
            return long_url

    def _dispatch_telegram_message(self, bot_token, chat_id, text, thread_link=""):
        """Send a single text message via the Telegram Bot API.

        When *thread_link* is provided an inline-keyboard button is attached
        so the user can tap it to open the Odoo record directly.
        If Telegram rejects the button (e.g. localhost URLs are invalid),
        a fallback message with the URL as plain text is sent instead.

        :param bot_token: Telegram Bot API token string.
        :param chat_id:   Telegram chat/user ID to send the message to.
        :param text:      Plain-text message body.
        :param thread_link: Optional URL for the inline button.
        """
        try:
            import requests as req  # soft import – library may not always be present

            api_url = "https://api.telegram.org/bot{}/sendMessage".format(bot_token)
            payload = {"chat_id": chat_id, "text": text}

            if thread_link:
                payload["reply_markup"] = {
                    "inline_keyboard": [
                        [{"text": "\U0001f517 Open With Odoo", "url": thread_link}]
                    ]
                }

            response = req.post(api_url, json=payload, timeout=10)

            if not response.ok and thread_link:
                # Telegram rejected the inline button (e.g. localhost URL).
                # Retry without button, appending the link as plain text.
                _logger.info(
                    "Inline button rejected for chat_id=%s (%s), "
                    "retrying with plain-text link.",
                    chat_id,
                    response.status_code,
                )
                fallback_payload = {
                    "chat_id": chat_id,
                    "text": "{}\n\nOpen With Odoo:\n{}".format(text, thread_link),
                }
                response = req.post(api_url, json=fallback_payload, timeout=10)

            if not response.ok:
                _logger.warning(
                    "Telegram API returned an error for chat_id=%s: %s %s",
                    chat_id,
                    response.status_code,
                    response.text,
                )
        except Exception as exc:
            _logger.warning(
                "Failed to deliver Telegram notification to chat_id=%s: %s",
                chat_id,
                exc,
            )
