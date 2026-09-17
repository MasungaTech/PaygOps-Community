from pony.orm import db_session
from shared.migrations.initial_setup.configure import create_default_app_menus as create_default_app_menus_initial_setup

@db_session
def up(db):
    create_default_app_menus_initial_setup()

@db_session
def down(db):
    pass
