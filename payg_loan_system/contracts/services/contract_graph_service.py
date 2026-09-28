from datetime import datetime, timedelta


class IndividualContractGraphService:

    @classmethod
    def get_contract_timeline_graph_data(cls, contract):
        return {
            'legend': cls.get_weekly_graph_data(contract),
            'data': [
                cls.get_expected_payments_graph_data(contract),
                cls.get_actual_payments_graph_data(contract)
            ]
        }

    @classmethod
    def get_contract_timeline_graph_data_for_usage_based(cls, contract):
        return {
            'legend': cls.get_weekly_graph_data(contract),
            'data': [
                cls.get_actual_payments_graph_data(contract)
            ]
        }

    @classmethod
    def get_actual_payments_graph_data(cls, contract):
        data = []
        last_total = contract.loan_addons_downpayments
        data.append({'x': contract.start_time, 'y': last_total})
        for repayment in contract.sorted_repayments():
            last_total += repayment.amount
            data.append({'x': repayment.time, 'y': last_total})
        if contract.end_time:
            end_time = contract.end_time
        else:
            end_time = datetime.now()
        data.append({'x': end_time, 'y': last_total})
        return data

    @classmethod
    def get_expected_payments_graph_data(cls, contract):
        data = []
        cumulative = 0
        for point in contract.get_expected_payments_table(cached=True):
            cumulative += point[1]
            data.append({'x': point[0], 'y': cumulative})
        return data

    @classmethod
    def get_weekly_graph_data(cls, contract):
        data =[]
        time = contract.start_time
        if contract.end_time:
            end_time = contract.end_time
        else:
            end_time = datetime.now()
        while time <= end_time:
            data.append(time)
            time += timedelta(days=7)
        return data
