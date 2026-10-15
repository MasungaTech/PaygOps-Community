import random
from datetime import timedelta, datetime

from core_system.core_entities import db
from accounting_system.accounting_db import accounting_db
from messages_system.models.sms_db import sms_db
from core_system.role.migrations.install_permissions import install_permissions
from shared.migrations.initial_setup import configure
from shared.migrations.models import DatabaseVersion
from tests.factories import user_mock
from tests.factories import location_mock
from tests.factories import offer_mock
from tests.factories import payment_mock
from sales_system.install import create_reasons_for_not_buying


class DatabaseSeeder:
    @staticmethod
    def create_db():
        db.drop_all_tables(with_all_data=True)
        DatabaseVersion.remove_version_table(db)
        accounting_db.drop_all_tables(with_all_data=True)
        sms_db.drop_all_tables(with_all_data=True)
        db.create_tables()
        accounting_db.create_tables()
        sms_db.create_tables()
        DatabaseVersion.create_version_table(db, time_type='datetime')
        DatabaseVersion.set_version(db, 1)

    @staticmethod
    def init_default_data():
        install_permissions()
        create_reasons_for_not_buying()
        user_mock.create_itmanager()
        configure.create_default_locations()
        location_mock.create_shops()
        location_mock.create_portfolio()
        user_mock.create_super_admin()
        user_mock.create_admin()
        user_mock.create_manager()
        this_agent = user_mock.create_agent()
        user_mock.create_agent_2()
        user_mock.create_view_only_user()
        user_mock.create_system_user()
        configure.create_system_surveys()
        configure.create_default_interaction_and_issue_topics()
        configure.create_default_accounts()
        configure.create_default_lead_statuses()
        configure.create_default_addons_categories()
        configure.create_default_lead_generator_types()
        configure.create_default_lead_generator()
        configure.create_default_offer()
        offer_mock.create_offers()
        payment_mock.create_payments()
        user_mock.create_devices()
        user_mock.create_lead_generator(3)
        user_mock.create_lead_generator(this_agent.id)
        user_mock.create_lead()
        user_mock.create_lead(date=fake_past_date(30))
        user_mock.create_lead(date=fake_past_date(15))
        user_mock.create_lead(date=fake_past_date(15))
        user_mock.create_lead()
        user_mock.create_picture()
        user_mock.generate_offline_token()
        user_mock.generate_offline_transaction()
        user_mock.generate_addon()


def fake_past_date(days_before):
    return datetime.now().replace(microsecond=0) - timedelta(days=days_before)
