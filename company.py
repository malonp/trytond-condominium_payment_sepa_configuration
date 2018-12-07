##############################################################################
#
#    GNU Condo: The Free Management Condominium System
#    Copyright (C) 2016- M. Alonso <port02.server@gmail.com>
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, If, Bool


__all__ = ['Company']


class Company(metaclass=PoolMeta):
    __name__ = 'company.company'

    company_account_number = fields.Many2One('bank.account.number', 'Default Account Number',
        ondelete='SET NULL',
        domain=[
            ('type', '=', 'iban'),
            If((Eval('company.party.active'), '=', True),
                                     [('account.active', '=', True),],
                                     []
            ),
            ('account.owners.companies', '=', Eval('id')),
            ],
        )
    company_sepa_batch_booking_selection = fields.Selection([
            (None, ''),
            ('1', 'Batch'),
            ('0', 'Per Transaction'),
             ], 'Default Booking',
        sort=False,)
    company_sepa_batch_booking = fields.Function(fields.Boolean('Default Booking'),
        getter='get_company_sepa_batch_booking',
        )
    company_sepa_charge_bearer = fields.Selection([
            (None, ''),
            ('DEBT', 'Debtor'),
            ('CRED', 'Creditor'),
            ('SHAR', 'Shared'),
            ('SLEV', 'Service Level'),
            ], 'Default Charge Bearer',
        sort=False,)

    @staticmethod
    def default_company_sepa_batch_booking_selection():
        Configuration = Pool().get('condo.payment.group.configuration')
        config = Configuration(1)
        if config.sepa_batch_booking_selection:
            return config.sepa_batch_booking_selection

    @staticmethod
    def default_company_sepa_charge_bearer():
        Configuration = Pool().get('condo.payment.group.configuration')
        config = Configuration(1)
        if config.sepa_charge_bearer:
            return config.sepa_charge_bearer

    def get_company_sepa_batch_booking(self, name):
        if self.company_sepa_batch_booking_selection == '1':
            return True
        elif self.company_sepa_batch_booking_selection == '0':
            return False
        return None
