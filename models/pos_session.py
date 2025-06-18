from odoo import models, api, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _create_combine_account_payment(self, payment_method, amounts, diff_amount):
        # Call original logic - or copy original method's code and add below
        outstanding_account = payment_method.outstanding_account_id
        destination_account = self._get_receivable_account(payment_method)

        account_payment = self.env['account.payment'].with_context(pos_payment=True).create({
            'amount': abs(amounts['amount']) + diff_amount,
            'journal_id': payment_method.journal_id.id,
            'force_outstanding_account_id': outstanding_account.id,
            'destination_account_id': destination_account.id,
            'memo': _('Combine %(payment_method)s POS payments from %(session)s',
                      payment_method=payment_method.name, session=self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
            'company_id': self.company_id.id,
        })

        # Adjust outstanding account for community
        accounting_installed = self.env['account.move']._get_invoice_in_payment_state() == 'in_payment'
        if not account_payment.outstanding_account_id and accounting_installed:
            account_payment.outstanding_account_id = account_payment._get_outstanding_account(
                account_payment.payment_type)

        if float_compare(amounts['amount'], 0, precision_rounding=self.currency_id.rounding) < 0:
            account_payment.write({
                'outstanding_account_id': account_payment.destination_account_id,
                'destination_account_id': account_payment.outstanding_account_id,
                'payment_type': 'outbound',
            })

        account_payment.action_post()

        if payment_method.parent_payment_method_name:
            # Search Journal
            journal = payment_method.journal_id
            if not journal:
                raise UserError(_('Please configure a Journal for bank transaction charge.'))

            commission_percent = getattr(journal, 'commission_tax_percentage', 0.0) or 0.0
            commission_fixed = getattr(journal, 'commission_tax_fix', 0.0) or 0.0

            total_difference = (amounts['amount'] * commission_percent / 100.0) + commission_fixed + diff_amount

            # After posting, adjust the posted journal entry lines:
            move_lines = account_payment.move_id.line_ids

            # Find outstanding account line
            outstanding_line = move_lines.filtered(lambda line: line.account_id == outstanding_account)
            if not outstanding_line:
                raise UserError(_('Could not find outstanding account line in payment move.'))
            outstanding_line = outstanding_line[0]

            # Reduce outstanding account line amount by total_difference
            # NOTE: debit or credit depends on payment_type and accounts used.
            # Let's assume debit side for simplicity (adjust if needed)
            new_debit = outstanding_line.debit - total_difference if outstanding_line.debit else 0.0
            new_credit = outstanding_line.credit - total_difference if outstanding_line.credit else 0.0

            # Defensive: don't allow negative amounts, handle correctly based on debit/credit presence
            vals = {}
            if outstanding_line.debit:
                vals['debit'] = max(new_debit, 0.0)
            if outstanding_line.credit:
                vals['credit'] = max(new_credit, 0.0)

            outstanding_line.write(vals)

            # Add new line for total_difference on suspense account
            self.env['account.move.line'].create({
                'name': _('Bank Transaction Charge'),
                'move_id': account_payment.move_id.id,
                'account_id': journal.suspense_account_id.id,
                'debit': total_difference if outstanding_line.debit else 0.0,
                'credit': total_difference if outstanding_line.credit else 0.0,
                'partner_id': account_payment.partner_id.id,
            })

        # Return receivable lines for further processing if needed
        return account_payment.move_id.line_ids.filtered(
            lambda line: line.account_id == self._get_receivable_account(payment_method)
        )



