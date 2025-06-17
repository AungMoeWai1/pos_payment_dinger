"""
This module defines the PaymentStatus model, which is used to
store the status information from the Dinger payment callback.
"""
from odoo import fields, models,api

from ..dataclasses.datamodels import JournalCodeEnum, TransactionStatusEnum


class PaymentStatus(models.Model):
    """To store the status information from the dinger payment call back.
    This model is used to keep track of the status of payment transactions
    received from the Dinger payment gateway. It captures details such as
    the transaction ID, reference number, merchant order ID, provider name,
    customer name, total amount, status, and the date and time when the payment
    was made. This information is essential for reconciling payments and
    providing accurate transaction records within the Odoo system.

    Args:
        models (_type_): _description_
    """
    _name = "pos.payment.status"
    _description = "To store the status information from the dinger payment call back"


    # That is transaction id from dinger
    reference = fields.Char(string="Reference")
    merchant_order = fields.Many2one(
        "pos.order",
        string="Merchant Order",
        help="Reference to the POS order associated with this payment status.",
    )
    provider_name = fields.Selection(selection=JournalCodeEnum.get_selection(), string="Provider Name")
    received_method = fields.Char(string="Received By")
    customer_name = fields.Char(string="Customer")
    # Here need to change float to monetary : fact- return value are float amount
    total = fields.Float(string="Total")
    state = fields.Selection(
        selection=TransactionStatusEnum.get_selection(),
        string="Status",
        default="draft",
    )
    paid_at = fields.Datetime(string="Paid At")

