from datetime import datetime, timedelta
from pony import orm
from data_system.analytical_db.models.contracts_history import Contracts_History
from shared.logger.loggers import LogAPI
from data_system.analytical_db.services.model_update_service import ModelUpdateService

log_api = LogAPI()


class AnalyticalDBStatsUpdateService:

    HISTORICAL_MODELS = [Contracts_History]

    @classmethod
    def update(cls):
        try:
            log_api.Event('Updating Historical Models...')
            for model in cls.HISTORICAL_MODELS:
                cls._update_historical_model(model)
        except Exception as e:
            log_api.FatalNoRequest(e)
            raise e

    @classmethod
    def _update_historical_model(cls, model):
        with orm.db_session(optimistic=False):
            last_updated = ModelUpdateService.get_last_update(model) 
            if last_updated == datetime.min:
                # If never updated, we get the oldest start date of a contract in the DB or max if no contracts
                last_updated = model.get_oldest_date() or datetime.max
        date_list = cls._get_month_dates_between_dates(last_updated, datetime.now())
        nb_dates = len(date_list)
        print(f'Dates to process: {nb_dates}')
        current_date = 0
        for from_date, to_date in date_list:
            current_date += 1
            print(f'Processing date: {current_date}/{nb_dates}')
            with orm.db_session(optimistic=False):
                # We remove anything that already exists for that date
                cls._clean_already_existing(model, from_date, to_date)
                orm.commit()
                ids_to_process = list(model.get_ids_for_dates(from_date, to_date))
            ModelUpdateService.update_model_objects(model, to_insert_ids=ids_to_process, from_date=from_date, to_date=to_date)

    @classmethod
    def _get_month_dates_between_dates(cls, first_date, now):
        to_date = datetime(now.year, now.month, 1) - timedelta(seconds=1)
        date_list = []
        while first_date < to_date:
            first_date, last_date = cls._get_first_and_last_date_in_month(first_date)
            date_list.append((first_date, last_date))
            first_date = last_date + timedelta(seconds=1)
        return date_list

    @classmethod
    def _get_first_and_last_date_in_month(cls, from_date):
        first_date = datetime(from_date.year, from_date.month, 1)
        next_month_date = first_date + timedelta(days=32)
        next_month_date = datetime(next_month_date.year, next_month_date.month, 1)
        last_date = next_month_date - timedelta(seconds=1) # 23:59:59 at the last day of the month
        return (first_date, last_date)

    @classmethod
    def _clean_already_existing(cls, model, from_date, to_date):
        to_remove = model.analytical_db_selector(from_date, to_date)
        to_remove.delete(bulk=True)
