from flask import request
from data_system.csv_exports.services.csv_export_service import CSVExportService
from shared.helpers.form_helpers import dateTimePickerToStandard
from shared.helpers.clock import Clock
from survey_system.models.forms import FormVersion


class CustomFormsExportService(CSVExportService):

    def _get_rows(self, data={}):
        from data_system.analytical_db.analytical_db import analytical_db
        try:
            analytical_db.generate_mapping()
        except Exception as e:
            pass
        qas = self.model.select().order_by(1)
        if 'form_id' in data:
            ids = [s.id for s in FormVersion.select(lambda s: s.form.id == data['form_id'])]
            qas = qas.filter(lambda qa: qa.form_id in ids)
        qas = self._date_filter(qas, data.get('from', ''))
        qas = self._date_filter(qas, data.get('to', ''),  lambda x, y: x <= y)
        return qas

    def _date_filter(self, qas, date_string, comparator=(lambda x, y: x >= y)):
        date = Clock.localize_to_utc(dateTimePickerToStandard(date_string))
        if date:
            qas = qas.filter(lambda qa: comparator(qa.date.date(),date))
        return qas
