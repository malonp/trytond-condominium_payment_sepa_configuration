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


import datetime
import logging

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['CondoPain', 'Group']


logger = logging.getLogger(__name__)


class CondoPain(metaclass=PoolMeta):
    __name__ = 'condo.payment.pain'

    @classmethod
    def __setup__(cls):
        super(CondoPain, cls).__setup__()
        cls._order.insert(0, ('reference', 'DESC'))


class Group(metaclass=PoolMeta):
    __name__ = 'condo.payment.group'

    @classmethod
    def __setup__(cls):
        super(Group, cls).__setup__()
        cls._order.insert(0, ('date', 'DESC'))
        cls._order.insert(1, ('reference', 'DESC'))

    @staticmethod
    def default_date():
        pool = Pool()
        Date = pool.get('ir.date')
        d = Date.today()
        # set tomorrow (or the next business day after tomorrow) as date
        next = d + datetime.timedelta(days=7 - d.weekday() if d.weekday() > 3 else 1)
        return next

    @classmethod
    def search_readonly(cls, name, domain):
        user = Transaction().user
        if user <= 1:
            return []

        super(Group, cls).search_readonly(name, domain)

    @classmethod
    def PreparePaymentGroup(cls, **kwargs):
        id = Transaction().context.get('company') or None

        if id:
            Company = Pool().get('company.company')
            condominium = Company(id)

            if (
                condominium
                and condominium.is_condo
                and condominium.sepa_creditor_identifier is not None
                and condominium.party.active
                and len(condominium.mandates) > 0
            ):

                bankaccountnumber = [
                    number
                    for account in condominium.party.bank_accounts
                    if account.active
                    for number in account.numbers
                    if number.type == 'iban'
                ]

                if (
                    (len(bankaccountnumber) == 1 or condominium.company_account_number)
                    and condominium.company_sepa_batch_booking is not None
                    and condominium.company_sepa_charge_bearer is not None
                ):
                    if 'dates' in kwargs:
                        # get biggest date
                        date = sorted([d[2] for d in filter(lambda x: not x[1], kwargs['dates'])], reverse=True)[0]

                    if date:
                        date_arg = date.date()
                        reference = (
                            '{:04d}'.format(date_arg.year)
                            + '_'
                            + '{:02d}'.format(date_arg.month)
                            + '-'
                            + (condominium.company_account_number or bankaccountnumber[0]).number_compact[8:12]
                            + '.'
                            + '{:04d}'.format(date_arg.year)[-2:]
                        )

                        payments = cls.search([('company', '=', condominium), ('reference', '=', reference)])
                        if not len(payments):
                            paymentgroup = cls(
                                reference=reference,
                                company=condominium,
                                account_number=condominium.company_account_number or bankaccountnumber[0],
                                date=date_arg,
                                sepa_batch_booking=condominium.company_sepa_batch_booking,
                                sepa_charge_bearer=condominium.company_sepa_charge_bearer,
                            )
                            paymentgroup.save()
                        else:
                            logger.error(
                                'Unable to create condo payment group with reference: %s for %s',
                                reference,
                                condominium.party.name,
                            )
            else:
                if condominium:
                    logger.error('Company %s dont check conditions to prepare payment group', condominium.party.name)
                else:
                    logger.error('Unable to prepare payment group. Cant find company with id: %s', id)
