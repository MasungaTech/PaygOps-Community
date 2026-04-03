from data_system.old_system.stats import StatsEngine


class AccountDashboard:
    @staticmethod
    def data(start_date, end_date, stats_engine=StatsEngine()):
        return stats_engine.generate_account_data(start_date, end_date)
