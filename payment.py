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


from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

import datetime


__all__ = ['CondoPain', 'CondoPaymentGroup']

class CondoPain:
    __metaclass__ = PoolMeta
    __name__ = 'condo.payment.pain'

    @classmethod
    def __setup__(cls):
        super(CondoPain, cls).__setup__()
        cls._order.insert(0, ('reference', 'DESC'))

class CondoPaymentGroup:
    __metaclass__ = PoolMeta
    __name__ = 'condo.payment.group'

    @classmethod
    def __setup__(cls):
        super(CondoPaymentGroup, cls).__setup__()
        cls._order.insert(0, ('reference', 'DESC'))

    @staticmethod
    def default_date():
        pool = Pool()
        Date = pool.get('ir.date')
        d = Date.today()
        #set tomorrow (or the next business day after tomorrow) as date
        next = d + datetime.timedelta(days= 7-d.weekday() if d.weekday()>3 else 1)
        return next

    @classmethod
    def search_readonly(cls, name, domain):
        user = Transaction().user
        if user<=1:
            return []

        super(CondoPaymentGroup, cls).search_readonly(name, domain)

    @classmethod
    def PreparePaymentGroup(cls, **kwargs):
        id = Transaction().context.get('company') or None

        if id:
            Company = Pool().get('company.company')
            condo = Company.search([('id', '=', id),
                                    ('is_Condominium', '=', True),
                                    ('sepa_creditor_identifier', '!=', None),
                                    ('party.active', '=', True),
                                  ])

            if (len(condo)==1 and len(condo[0].sepa_mandates)>0):
                bankaccountnumber = [ b for b in condo[0].party.bank_accounts if b.account.active and b.type=='iban' ]

                if (len(bankaccountnumber)==1 or condo[0].company_account_number) and\
                    condo[0].company_sepa_batch_booking is not None and\
                    condo[0].company_sepa_charge_bearer is not None:
                    if 'dates' in kwargs:
                        #get biggest date
                        date = sorted([d[2] for d in filter(lambda x:not x[1], kwargs['dates'])], reverse=True)[0]

                    if date:
                        date_arg = date.date()
                        paymentgroup = cls(reference = '{:04d}'.format(date_arg.year) +
                                                       '_' +
                                                       '{:02d}'.format(date_arg.month) +
                                                       '-' +
                                                       bankaccountnumber[0].number_compact [8:12] +
                                                       '.' +
                                                       '{:04d}'.format(date_arg.year)[-2:],
                                           company = condo[0],
                                           account_number = condo[0].company_account_number or bankaccountnumber[0],
                                           date = date_arg,
                                           sepa_batch_booking = condo[0].company_sepa_batch_booking,
                                           sepa_charge_bearer = condo[0].company_sepa_charge_bearer,
                                           )
                        paymentgroup.save()
