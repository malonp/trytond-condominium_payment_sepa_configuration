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


from sql.aggregate import Count, Max

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
                BankAccountNumber = Pool().get('bank.account.number')
                bankaccountnumber = BankAccountNumber.search([('account.id', 'in', condo[0].party.bank_accounts),
                                                              ('account.active', '=', True),
                                                              ('type', '=', 'iban'),
                                                             ])
                if len(bankaccountnumber)==1: #Only condos with one bank account number
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
                                           account_number = bankaccountnumber[0],
                                           date = date_arg,
                                           sepa_charge_bearer = 'SLEV')
                        paymentgroup.save()

    @classmethod
    def PrepareAllPaymentsGroup(cls):
        pool = Pool()
        banknumbers = pool.get('bank.account.number').__table__()
        bankaccounts = pool.get('bank.account').__table__()
        accountparties = pool.get('bank.account-party.party').__table__()
        parties = pool.get('party.party').__table__()
        companies = pool.get('company.company').__table__()

        cursor = Transaction().cursor

        #SELECT a.id, a.number, e.id, d.id, d.name FROM bank_account_number AS a
        #    INNER JOIN bank_account AS b ON a.account=b.id
        #    INNER JOIN "bank_account-party_party" AS c ON b.id=c.account
        #    INNER JOIN party_party AS d ON c.owner=d.id
        #    INNER JOIN company_company AS e ON d.id=e.party
        # WHERE a.type='iban' AND b.active<>0 AND d.active<>0 AND e.is_Condominium<>0 AND e.sepa_creditor_identifier<>""
        # GROUP BY e.id
        # HAVING COUNT(e.id)=1
        # ORDER BY e.id;
        cursor.execute(*banknumbers.join(bankaccounts,
                                     condition=banknumbers.account == bankaccounts.id).join(
                                     accountparties,
                                     condition=bankaccounts.id == accountparties.account).join(
                                     parties,
                                     condition=accountparties.owner == parties.id).join(
                                     companies,
                                     condition=parties.id == companies.party).select(
                                     Max(banknumbers.id), Max(banknumbers.number_compact), companies.id,
                                     where=((banknumbers.type == 'iban') &
                                            (bankaccounts.active == True) &
                                            (parties.active == True) &
                                            (companies.is_Condominium == True) &
                                            (companies.sepa_creditor_identifier != None)),
                                     group_by=companies.id,
                                     having=(Count(companies.id)==1)))

        Date = pool.get('ir.date')
        d = Date.today()
        ddd = d.replace(day = 2,
                        month = d.month+1 if d.month<12 else 1,
                        year = d.year if d.month<12 else d.year+1)

        #TODO: Check that condo has mandates
        values = []
        for (idb, number_compact, idc) in cursor.fetchall():
            record = {
                    'reference':          '{:04d}'.format(ddd.year) +
                                          '_' +
                                          '{:02d}'.format(ddd.month) +
                                          '-' +
                                          number_compact [8:12] +
                                          '.' +
                                          '{:04d}'.format(ddd.year)[-2:],
                    'company':            idc,
                    'account_number':     idb,
                    'date':               ddd + datetime.timedelta(days= 2 if ddd.weekday()>4 else 0),
                    'sepa_charge_bearer': 'SLEV'
                   }
            values.append(record)

        cls.create(values)

