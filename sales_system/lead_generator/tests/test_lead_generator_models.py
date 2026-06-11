from mock import MagicMock
import pytest
from pony.orm import db_session
from sales_system.lead_generator.model import LeadGenerator
from datetime import datetime, timedelta


class TestLeadGenerator:

    @db_session
    def test_seniority_by_month_returns_zero(self):
        lead_generator = LeadGenerator.select().first()
        lead_generator.start_date = datetime.now()

        assert '0m' == lead_generator.seniority_by_month()

    @db_session
    def test_seniority_by_month_returns_one_month(self):
        lead_generator = LeadGenerator.select().first()
        lead_generator.start_date = datetime.now() - timedelta(days=31)

        assert '1m' == lead_generator.seniority_by_month()

    @db_session
    def test_seniority_by_month_returns_two_months(self):
        lead_generator = LeadGenerator.select().first()
        lead_generator.start_date = datetime.now() - timedelta(days=60)

        assert '2m' == lead_generator.seniority_by_month()
