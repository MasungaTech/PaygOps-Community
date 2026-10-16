from pony.orm import db_session
from app_builder_system.automations.models.automation_model import Automation
from shared.migrations.migration_helper import add_column_from_model_property, drop_column

@db_session
def up(db):
    add_column_from_model_property(Automation.step_by_step_description) 

@db_session
def down(db):
    drop_column(db, "automation", "step_by_step_description")
