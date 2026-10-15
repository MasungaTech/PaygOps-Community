from accounting_system.accounting_interface import Expense, getCurrentUserById
from sales_system.leads.services.lead_getter_service import LeadGetterService
from pony import orm
from datetime import datetime



class LeadGeneratorCommissionService:

    def process_commissions(lead_generator, user, lead_ids, create_expenses=False):
        totalCommissionAmount = 0
        if create_expenses:
            expenseDescription = "Payment for lead commissions to " + lead_generator.person.full_name + " for Leads number: "
        for id in lead_ids:
            ThisLead = LeadGetterService.get_from_user_and_id(user, id, strict=True)
            if ThisLead.commission:
                totalCommissionAmount += int(ThisLead.commission)
            ThisLead.commission_paid = True
            if create_expenses:
                expenseDescription += str(id)
                if ThisLead.commission:
                    expenseDescription += ' (' + str(ThisLead.commission) + '), '
                else:
                    expenseDescription += ' (0), '

        if create_expenses and totalCommissionAmount > 0:
            currentAccountingUser = getCurrentUserById(user.id)

            if lead_generator.person.user and lead_generator.person.user.organization == 'Internal':
                expenseCategory = 'Employee Commission'
            else:
                expenseCategory = 'External Commission'

            expenseAccount = currentAccountingUser.getFirstAccount()

            thisExpense = Expense(date=datetime.now(),
                                  entryDate=datetime.now(),
                                  amount=float(totalCommissionAmount),
                                  description=expenseDescription,
                                  account=expenseAccount,
                                  reportedBy=currentAccountingUser,
                                  category=expenseCategory)
        return_value = {
            'commissions_paid': len(lead_ids), 
            'total_commission_amount': totalCommissionAmount, 
        }
        orm.commit()
        if create_expenses:
            return_value['expense_id'] = thisExpense.id
        return return_value
