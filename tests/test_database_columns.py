from core_system.core_entities import db
from pony.orm import Set, db_session

class TestDatabaseColumns():
    
    @db_session
    def test_database_columns(self):
        for entity in db.entities.values():
            for attr in entity._attrs_:
                if not isinstance(attr, Set) and not isinstance(attr.reverse, Set) and attr.is_relation:
                    if attr.column and attr.reverse.column and attr != attr.reverse:
                        raise Exception(f'Attributes {attr} and {attr.reverse} both define columns')
