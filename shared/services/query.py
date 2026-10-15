

class QueryService:

    @staticmethod
    def filter_active_clients(clients):
        return clients.filter(lambda c: c.active)
