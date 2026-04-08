from core_system.operational_entities.models import Cluster
from core_system.core_entities import db
from core_system.users.models.user_model import User
from core_system.portfolios.model import PortfolioEntity
from datetime import datetime
from pony.orm import *


@db_session
def create_shops():
    user = User.select().first()
    for n in range(1, 7):
        name = 'Shop%s' % n
        db.Hub(name=name, user_in_charge=user, parent=db.Zone.select().first())


@db_session
def create_management_cluster():
    return Cluster(name='Cluster1', user_in_charge=User[3], parent=User[3].shop)


@db_session
def create_portfolio():
    PortfolioEntity(
        name='Example Portfolio',
        description='Example',
        budget=12300,
        creation_datetime=str(datetime.now())
    )
