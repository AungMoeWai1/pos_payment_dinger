import json
from odoo import http
from odoo.http import request, route
from odoo import fields
from datetime import datetime

from .decryption_aes_ecb_pkcs7padding import decrypt


@staticmethod
def convert_paid_at(date_str: str) -> str:
    """Convert the date string from Dinger format to Odoo format."""
    return datetime.strptime(date_str, "%Y%m%d %H%M%S").strftime("%Y-%m-%d %H:%M:%S")

@staticmethod
def create_new_pos_payment_status(data):
    merchant_order = data.get('merchantOrderId')  # This is order.name
    transaction = data.get('transactionId')
    status = data.get('transactionStatus')
    total_amount = data.get('totalAmount')
    created_at = data.get('createdAt')
    provider_name = data.get('providerName')
    method_name = data.get('methodName')
    customer_name = data.get('customerName')

    # Find the payment status record for this order
    payment_status = request.env['pos.payment.status'].sudo().search([('merchant_order', '=', merchant_order)],
                                                                     limit=1)
    if payment_status:
        # For existing record , update the filed values
        payment_status.reference=transaction
        payment_status.provider_name= provider_name
        payment_status.received_method=method_name
        payment_status.customer_name=customer_name
        payment_status.total=total_amount
        payment_status.state = status
        payment_status.paid_at = convert_paid_at(created_at)
    else:
        # create a new record
        request.env['pos.payment.status'].sudo().create({
            'reference': transaction,
            'merchant_order': merchant_order,
            'provider_name': provider_name,
            'received_method': method_name,
            'customer_name': customer_name,
            'total': total_amount,
            'state': status,
            'paid_at': datetime.now()
        })


class PosOrderController(http.Controller):
    _webhook_url = '/pos/order/dinger_payment_method'

    # Here dinger make return url and need to modify prebuilt_popup of qr image with check mark
    @route(_webhook_url, type="http", auth="none", csrf=False, methods=["POST"])
    def render_order_types(self):
        data = request.httprequest.get_json(force=True)
        # payment_result = post.get('paymentResult')
        # check_sum = post.get('checksum')

        # Decrypt the payment result
        # decrypted_str = decrypt(self.secret_key, payment_result)

        # try:
        #     result = json.loads(decrypted_str)
        # except json.JSONDecodeError:
        #     print("Failed to parse decrypted data as JSON:")
        #     print(decrypted_sfrom serial.tools.miniterm import Printabletr)
        #     raise

        # ref = result.get('merchantOrderId')  # This is order.name
        # payment_id = result.get('transactionId')
        # status = result.get('transactionStatus')
        # total_amount = result.get('totalAmount')
        # created_at = result.get('createdAt')
        # provider_name = result.get('providerName')
        # method_name = result.get('methodName')
        # customer_name = result.get('customerName')

        # data = request.jsonrequest
        ref = data.get('order_name')
        status = data.get('status')

        # Find the POS order
        pos_order = request.env['pos.order'].sudo().search([('name', '=', ref)], limit=1)
        if pos_order:
            # Find the payment status record for this order
            payment_status = request.env['pos.payment.status'].sudo().search([('merchant_order', '=', pos_order.pos_reference)],
                                                                             limit=1)
            if payment_status:
                payment_status.state = status  # Update the status field
            else:
                # Optionally, create a new record if not found
                request.env['pos.payment.status'].sudo().create({
                    'merchant_order': pos_order.pos_reference,
                    'state': status,
                    'paid_at': fields.Datetime.now(),
                    # Add other fields if needed
                })

        print("Status is :", status)

        return {'result': 'Live data sent successfully'}

    @http.route('/pos/payment_status/create_draft', type='json', auth='user', csrf=False, methods=['POST'])
    def create_payment_status_draft(self, **kwargs):

        create_new_pos_payment_status(kwargs)
        return "Data record created successfully"