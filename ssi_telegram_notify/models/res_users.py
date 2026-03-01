from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    telegram_chat_id = fields.Char(
        string="Telegram Chat ID",
        help="Your personal Telegram Chat ID. "
        "The Telegram bot must be started in your chat before notifications can be sent.",
    )
    notify_via_telegram = fields.Boolean(
        string="Notify via Telegram",
        default=False,
        help="When enabled, Odoo thread notifications will also be forwarded "
        "to your Telegram account.",
    )
