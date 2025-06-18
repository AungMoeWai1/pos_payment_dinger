from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dinger_payment_terminal = fields.Boolean(string="Dinger Payment Terminal",
                                             config_parameter='pos_payment_dinger.enabled',
                                             help="The transactions are processed by Dinger. Set your Dinger credentials on the related payment method.")

