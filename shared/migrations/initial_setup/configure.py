import os
import random

from core_system.role.models import Role
from pony.orm import db_session, flush

from accounting_system.install import (createCompanyAccounts,
                                       createDepartmentAccounts)
from core_system.operational_entities.services.edit_operational_entity_service import \
    EditOperationalEntityService
from core_system.role.methods.getters import get_role_from_name
from core_system.users.models.user_model import User
from core_system.users.services.edit_user_service import EditUserService
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from payg_loan_system.contracts.models.addons_model import (AddOnOffer,
                                                            AddOnType)
from payg_loan_system.contracts.services.addons.addon_offer_service import \
    AddonOfferService
from payg_loan_system.offers.services.create_offer_service import \
    CreateOfferService
from sales_system.lead_generator.services.lead_generator_edit_service import \
    LeadGeneratorEditService
from sales_system.leads.services.lead_status_service import LeadStatusService
from shared.helpers.auth_helper import encode_password
from shared.migrations.commands.migrate_report_topics import createReportTopics
from survey_system.system_surveys.create_system_surveys import \
    create_all_system_surveys
from core_system.role.services import RoleGetterService

import config


# Default initial admin credentials resolved once (env var with fallback)
INITIAL_ADMIN_EMAIL = os.getenv('INITIAL_ADMIN_EMAIL', "admin@example.com")
INITIAL_ADMIN_PASSWORD = os.getenv('INITIAL_ADMIN_PASSWORD', "changeme123")


@db_session
def create_default_locations():
    admin_email = INITIAL_ADMIN_EMAIL
    if admin_email:
        user_in_charge = User.get(username=admin_email)

    default_region = EditOperationalEntityService.add_from_data_and_user({
        'name': "Default Region",
        'user_in_charge_id': user_in_charge.id,
        'level': 4
    }, user=user_in_charge)
    flush()
    default_zone = EditOperationalEntityService.add_from_data_and_user({
        'name': "Default Zone",
        "level": 3,
        "parent_id": default_region.id,
        'user_in_charge_id': user_in_charge.id
    }, user_in_charge)
    flush()
    default_shop = EditOperationalEntityService.add_from_data_and_user({
        'name': 'Headquarters',
        "level": 2,
        "parent_id": default_zone.id,
        'user_in_charge_id': user_in_charge.id
    }, user_in_charge)
    default_shop.reference_of_users.add(User.select())
    flush()
    default_cluster = EditOperationalEntityService.add_from_data_and_user({
        'name': 'Default Cluster',
        "level": 1,
        "parent_id": default_shop.id
    }, user_in_charge)
    flush()
    EditOperationalEntityService.add_from_data_and_user({
        'name': 'Default Village',
        "level": 0,
        'parent_id': default_cluster.id
    }, user_in_charge)


@db_session
def create_default_addons_categories():
    admin_email = INITIAL_ADMIN_EMAIL
    user = None
    if admin_email:
        user = User.get(username=admin_email)
    if not AddOnCategory.get(name="Product"):
        AddOnCategory(
            name="Product"
        )
    if not AddOnCategory.get(name="Service"):
        AddOnCategory(
            name="Service"
        )
    if not AddOnCategory.get(name="Contract Terms Changes"):
        AddOnCategory(
            name="Contract Terms Changes"
        )
    if not AddOnCategory.get(name="Purchasing"):
        AddOnCategory(
            name="Purchasing"
        )
    if not AddOnOffer.get(code='ADD_ONE_DAY'):
        AddonOfferService.add_from_data_and_user({
            'name': "Add 1 day",
            'code': 'ADD_ONE_DAY',
            'price': 0,
            'duration_change': 1,
            'category': "Contract Terms Changes",
            'type': AddOnType.loan_duration_change,
            'need_approval': True,
            'available_for_registration': False,
            'available_for_sales': False,
            'allow_decimal_quantities': True
        }, user, force=True)
    if not AddOnOffer.get(code='REDUCE_ONE_DAY'):
        AddonOfferService.add_from_data_and_user({
            'name': "Reduce 1 day",
            'code': 'REDUCE_ONE_DAY',
            'price': 0,
            'duration_change': -1,
            'category': "Contract Terms Changes",
            'type': AddOnType.loan_duration_change,
            'need_approval': True,
            'available_for_registration': False,
            'available_for_sales': False,
            'allow_decimal_quantities': True
        }, user, force=True)
    if not AddOnOffer.get(code='REDUCE_DEPOSIT'):
        AddonOfferService.add_from_data_and_user({
            'name': "Deposit Reduction",
            'code': 'REDUCE_DEPOSIT',
            'price': 0,
            'downpayment': -1,
            'category': "Contract Terms Changes",
            'type': AddOnType.deposit_change,
            'need_approval': True,
            'available_for_registration': True,
            'available_for_sales': False,
            'allow_decimal_quantities': True
        }, user, force=True)
    if not AddOnOffer.get(code='INCREASE_DEPOSIT'):
        AddonOfferService.add_from_data_and_user({
            'name': "Increase Deposit",
            'code': 'INCREASE_DEPOSIT',
            'price': 0,
            'downpayment': 1,
            'category': "Contract Terms Changes",
            'type': AddOnType.deposit_change,
            'need_approval': True,
            'available_for_registration': True,
            'available_for_sales': False,
            'allow_decimal_quantities': True
        }, user, force=True)


@db_session
def create_default_lead_statuses():
    LeadStatusService.edit_statuses({
        'to_be_convinced': [
            {'id': 15, 'name':'Hesitating', 'color': 'gray'},
            {'id': 14, 'name':'Very Interested', 'color': 'blue'}
        ],
        'awaiting_information': [
            {'id': 12, 'name':'Ready to Buy', 'color': 'green'},
            {'id': 9, 'name':'Awaiting lead information', 'color': 'black'}
        ],
        'awaiting_decision': [
            {'id': 8, 'name':'Awaiting loan approval', 'color': 'purple'},
        ],
        'awaiting_payment': [
            {'id': 3, 'name':'Awaiting Payment', 'color': 'amber'}
        ],
        'awaiting_delivery': [
            {'id': 2, 'name':'Awaiting Delivery', 'color': 'blue'}
        ],
        'installed': [
            {'id': 1, 'name':'Installed', 'color': 'green'}
        ],
        'inactive': [
            {'id': 18, 'name':'No Longer Interested', 'color': 'black'},
            {'id': 11, 'name':'Loan Denied - Awaiting Information', 'color': 'black'},
            {'id': 19, 'name':'Loan Denied - Insufficient Income', 'color': 'black'},
            {'id': 20, 'name':'Loan Denied - Too Far', 'color': 'black'},
            {'id': 21, 'name':'Loan Denied - Other Reason', 'color': 'black'}
        ],
        'discarded': [
            {'id': 22, 'name':'Discarded', 'color': 'black'}
        ],
        'cancelled' : [
            {'id': 23, 'name':'Cancelled', 'color': 'black'}
        ]
    })


@db_session
def create_admin_user():
    admin_password = INITIAL_ADMIN_PASSWORD
    advisory_password = os.getenv('INITIAL_ADVISORY_PASSWORD', '')
    finance_password = os.getenv('INITIAL_FINANCE_PASSWORD', '')
    
    # Admin user email (resolved once at module level)
    admin_email = INITIAL_ADMIN_EMAIL
    advisory_email = os.getenv('INITIAL_ADVISORY_EMAIL', '')
    system_email = os.getenv('INITIAL_SYSTEM_EMAIL', config.SYSTEM_EMAIL)
    finance_email = os.getenv('INITIAL_FINANCE_EMAIL', '')

    if not admin_email or not admin_password:
        raise Exception('INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD are not set')
    EditUserService.add_user(
        None,
        name='Solaris', surname='Admin', username=admin_email, email=admin_email, hub=None, # Reference Entity set after creating entities
        password=encode_password(admin_password), role=get_role_from_name('SuperAdmin'), organization='Solaris Offgrid'
    )
    secret_pass = ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyz!$%&/\()=*.+-') for n in range(20))
    if system_email:
        system = EditUserService.add_user(
            None,
            name='System', surname='User', username=system_email, email=system_email, hub=None, # Reference Entity set after creating entities
            password=encode_password(secret_pass), role=get_role_from_name('SuperAdmin'), organization='Solaris Offgrid'
        )
    if advisory_email:
        EditUserService.add_user(
            None,
            name='Solaris', surname='Advisory', username=advisory_email, email=advisory_email, hub=None, # Reference Entity set after creating entities
            password=encode_password(advisory_password), role=get_role_from_name('SuperAdmin'), organization='Solaris Offgrid'
        )
    if finance_email:
        EditUserService.add_user(
            system,
            name='Metrics', surname="Service",
            username=finance_email,
            email=finance_email,
            hub=None, # Reference Entity set after creating entities
            password=encode_password(finance_password),
            role=get_role_from_name('Metrics API'),
            organization='Solaris Offgrid'
        )

@db_session
def create_system_surveys():
    create_all_system_surveys()


@db_session
def create_default_interaction_and_issue_topics():
    if config.ENABLE_ENTERPRISE_FEATURES:
        createReportTopics()
    else:
        return


@db_session
def create_default_accounts():
    createCompanyAccounts()
    createDepartmentAccounts()


@db_session()
def create_default_offer():
    admin_email = INITIAL_ADMIN_EMAIL
    if admin_email:
        user = User.get(username=admin_email)
    data={
        'name': 'Ticketing Default Offer',
        'code': 'TDO',
        'approval_required': 'No',
        'family': 'Business',
        'base_price_amount': 1,
        'base_credit_amount': 1,
        'downpayment': 0,
        'type':'Usage Based',
        'free_credit_at_start':1,
        'credit_unit': 'days',
        'base_price_credit': 1,
        'base_price_unit': 1
    }
    CreateOfferService.add_from_data_and_user(data=data, user=user)

@db_session
def create_default_lead_generator_types():
    from constants import DEFAULT_LEAD_GENERATOR_TYPES
    from sales_system.lead_generator.model import LeadGeneratorType
    for lgt in DEFAULT_LEAD_GENERATOR_TYPES:
        LeadGeneratorType(name=lgt)

@db_session
def create_default_lead_generator():
    user = User.get(username=config.SYSTEM_EMAIL)
    data = {
                'name': 'Default',
                'surname': 'Lead Generator',
                'type': 'Default Lead Generator'
            }
    default_generator = LeadGeneratorEditService.add_from_data_and_user(
        data=data, user=user
    )


@db_session
def check_superadmin_users_are_solarisoffgrid():
    role = Role.get(name='Administrator')
    if role:
        current_user = User.get(username=config.SYSTEM_EMAIL)
        users =  User.select()
        users = users.filter(lambda u: u.AuthorizationLevel.name == 'SuperAdmin')
        for user in users[:]:
            if not user.email.endswith('@solarisoffgrid.com'):
                EditUserService.edit_user_from_data(
                    current_user, {
                        'role_id': role.id,
                        'username': user.username
                    }, 
                    user
                )
