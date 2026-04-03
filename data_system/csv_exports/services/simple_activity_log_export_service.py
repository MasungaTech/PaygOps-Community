import io
import csv
import json
import os
import zipfile
from constants import TEMP_PATH
from shared.model.activity_log_model import ActivityLogEntry
from shared.services.activity_log_service import ActivityLogGetter
from data_system.csv_exports.services.page_processor_service import CSVPageProcessorService


class SimpleActivityLogExportService:

    @classmethod
    def get_simple_export(cls, last_id, filename):

        temp_file_path = TEMP_PATH+'activity_log_data.csv'
        with open(temp_file_path, 'w') as file:
            csv_writer = csv.writer(file)
            cls._write_headers(csv_writer)
            cls._write_data(csv_writer, last_id)

        zip_file = zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED)
        zip_file.write(temp_file_path, 'activity_log_data.csv')
        zip_file.close()

        try: os.remove(temp_file_path)
        except: pass

    @classmethod
    def _write_headers(cls, writer):
        headers = [
            'Time',
            'User ID',
            'IP',
            'Path',
            'Args',
            'Data',
            'App',
            'User Agent'
        ]
        writer.writerow(headers)

    @classmethod
    def _write_data(cls, writer, last_id):

        entries = ActivityLogGetter.get_list(last_id=last_id).prefetch(ActivityLogEntry.args, ActivityLogEntry.data, ActivityLogEntry.user_agent)
        
        CSVPageProcessorService.process_by_page(
            input_data=entries,
            processing_function=cls._write_data_for_entries,
            writer=writer
        )

    @classmethod
    def _write_data_for_entries(cls, entries, writer):

        for entry in entries:
            content = [
                cls._basic_datetime_for_sheet(entry.time),
                entry.user if entry.user else 'PaygOps Services',
                entry.ip,
                entry.path,
                json.dumps(entry.args),
                json.dumps(entry.data),
                entry.app,
                json.dumps(entry.user_agent)
            ]
            writer.writerow(content)

    @classmethod
    def _basic_datetime_for_sheet(cls, date):
        if date is not None:
            return date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return ''
