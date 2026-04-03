from datetime import date, datetime, time, timedelta
from decimal import Decimal
import csv
import json
from constants import DATA_EXPORT_LIMIT
from data_system.csv_exports.services.page_processor_service import CSVPageProcessorService
from shared.logger.loggers import LogAPI
from pony.orm import desc
import config
import os, io

logger = LogAPI()


class CSVWriterWithFlush:
    def __init__(self, file_obj):
        self.file = file_obj
        self.writer = csv.writer(file_obj)

    def writerow(self, row):
        self.writer.writerow(row)

    def flush(self):
        self.file.flush()
        os.fsync(self.file.fileno())


class CSVExportService:

    def __init__(self, model, page_size=None):
        from data_system.analytical_db.analytical_db import analytical_db
        if model:
            self.model = getattr(analytical_db, model)
        if not page_size:
            # We put a lower global size on small server as they are more RAM limited
            if config.GLOBAL_SCALE < 8:
                page_size = 1000
            else:
                page_size = 2500
        self.page_size = page_size
        self.data_limit = DATA_EXPORT_LIMIT

    def get_simple_export(self, data={}, file_path=None):
        if not file_path:
            raise ValueError("file_path is required")
            
        with open(file_path, 'w', newline='') as file:
            csv_writer = CSVWriterWithFlush(file)
            self._write_headers(csv_writer)
            self._write_data(csv_writer, data)
        return file_path

    @staticmethod
    def _format_header(h):
        return ' '.join([w.capitalize() for w in h.split('_')])

    def _write_headers(self, writer):
        headers = []
        for attr in self.get_attributes():
            if attr.is_relation and attr.csv_columns:
                # We add the ID column itself unless the first object in csv_columns is "False"
                if attr.csv_columns[0] != False:
                    headers += [self._format_header(attr.name)]
                for item in attr.csv_columns:
                    headers.append(item[0])
            else:
                headers += [self._format_header(attr.name)]
        writer.writerow(headers)

    def _get_rows(self, data={}):
        query = self.model.select().order_by(desc(self.model.id))
        return query

    def get_attributes(self):
        return [attr for attr in self.model._attrs_ if attr.column]

    def _get_content(self, row):
        content = []
        for attr in self.get_attributes():
            value = getattr(row, attr.name)
            if attr.is_relation:
                referenced_entity = value
                if attr.csv_columns:
                    # We add the ID column itself unless the first object in csv_columns is "False"
                    if attr.csv_columns[0] != False:
                        content.append(self._format_value(referenced_entity.id) if referenced_entity else '')
                    content += [self._format_value(f[1](referenced_entity)) if referenced_entity else '' for f in attr.csv_columns]
                else:
                    content.append(self._format_value(referenced_entity.id) if referenced_entity else '')
            elif attr.precision:
                content.append(self._format_value(value, attr.precision))
            elif attr.force_time:
                content.append(self._format_value(value, force_time=attr.force_time))
            else:
                content.append(self._format_value(value))
        return content

    def _format_value(self, value, precision=2, force_time=None):
        if isinstance(value, datetime):
           return self._basic_datetime_for_sheet(value, force_time)
        elif isinstance(value, date):
           return self._basic_date_for_sheet(value)
        elif isinstance(value, time):
           return self._basic_time_for_sheet(value)
        elif isinstance(value, float) or isinstance(value, Decimal):
            return "{:.{}f}".format(value, precision)
        return value

    def _write_data(self, writer, data={}):
        if self._there_is_data(data):
            rows = self._get_rows(data=data)
        else:
            rows = self._get_rows()
        params = {
            'input_data': rows,
            'processing_function': self._processor,
            'writer': writer,
            'data_limit': self.data_limit,
        }
        if self.page_size:
            params['page_size'] = self.page_size
        CSVPageProcessorService.process_by_page(**params)

    def _there_is_data(self, data):
        clean_data = dict(data.copy())
        clean_data.pop('key', None)
        clean_data.pop('email_user_id', None)
        return bool(clean_data)

    def _processor(self, rows, writer):
        for row in rows:
            try:
                writer.writerow(self._get_content(row))
            except Exception as error:
                logger.Fatal(error)
        # We flush the file to disk to clear the RAM
        writer.flush()

    def _basic_datetime_for_sheet(self, date, force_time=None):
        if force_time and date:
            return (date).strftime("%Y-%m-%d")
        return date.strftime("%Y-%m-%d %H:%M") if date is not None else ''

    def _basic_date_for_sheet(self, date):
        return date.strftime("%Y-%m-%d") if date is not None else ''
        
    def _basic_time_for_sheet(self, time):
        return time.isoformat(timespec="seconds") if time is not None else 'Never'
    
    def get_data_list_csv(self, data_list, columns=None):
        data = [json.loads(line) for line in data_list if line.strip()]

        if data and not columns:
            columns = data[0].keys()

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)

        return output
