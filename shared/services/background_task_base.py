import csv
import io
import json
from config import ENV_VAR
from shared.logger.loggers import Error
from shared.cache.redis_config import delete_cache_key, get_cache_key, set_cache_key
from worker_app.worker_app import worker_app

class BackgroundTask:

    analysis_task_id = None
    process_task_id = None
    status = None
    analysis = None
    data = None
    file = None
    user = None
    processing_errors = []

    ATTRIBUTES = {
        'analysis_task_id': ['text', '_analysing_task'],
        'process_task_id': ['text', '_processing_task'],
        'status': ['text', '_status'],
        'analysis': ['json', '_analysis'],
        'data': ['json', '_data'],
        'processing_errors': ['json', '_processing_errors'],
        'file': ['text', '_file'],
        'has_headers': ['text', '_has_headers'],
        'user': ['text', '_user'],
        'user_ip': ['text', '_user_ip'],
        'user_agent': ['text', '_user_agent'],
        'request': ['json', '_request'],
        'entity': ['text', '_entity'],
        'headers': ['json', '_headers'],
        'action': ['text', '_action'], # only for API caller
        'unordered': ['text', '_unordered'], # when 'true', order is not important
        'analysis_progress': ['json', '_analysis_progress'], # progress tracking for analysis
        'processing_progress': ['json', '_processing_progress'], # progress tracking for processing
    }

    def __init__(self, uuid, entity=None, config=None):
        self.uuid = uuid
        if entity:
            self.entity = entity
        if config:
            self.display_name, self.analysis_task = config[self.entity]
        self.check_status()

    def __getattribute__(self, name):
        if ENV_VAR == 'TEST': raise Error('Background tasks not available in test mode')
        if not name in BackgroundTask.ATTRIBUTES:
           return super(BackgroundTask, self).__getattribute__(name)
        kind = BackgroundTask.ATTRIBUTES[name][0]
        value = get_cache_key(self.uuid+BackgroundTask.ATTRIBUTES[name][1])
        return json.loads(value or '{}') if kind == 'json' else value

    def __setattr__(self, name, value):
        if not name in BackgroundTask.ATTRIBUTES:
            return super(BackgroundTask, self).__setattr__(name, value)
        kind = BackgroundTask.ATTRIBUTES[name][0]
        key = self.uuid+BackgroundTask.ATTRIBUTES[name][1]
        set_cache_key(key, json.dumps(value) if kind == 'json' else value)

    def __delattr__(self, name):
        if not name in BackgroundTask.ATTRIBUTES:
            raise AttributeError
        key = self.uuid+BackgroundTask.ATTRIBUTES[name][1]
        delete_cache_key(key)
    
    def check_status(self):
        if (self.analysis_task_id and worker_app.AsyncResult(self.analysis_task_id).failed() or 
            self.process_task_id and worker_app.AsyncResult(self.process_task_id).failed()):
            del self.analysis_task_id
            del self.process_task_id
            self.status = 'error'

    def process(self):
        self.process_task_id = worker_app.send_task(
            'worker_app.tasks.process_bulk_entity_upload.process_bulk_entity_upload',
            args=([self.uuid])
        ).id

    def cancel(self):
        worker_app.control.revoke(self.analysis_task_id, terminate=True)
        worker_app.control.revoke(self.process_task_id, terminate=True)
        del self.analysis_task_id
        del self.process_task_id
        del self.status
        del self.has_headers
        del self.headers
        del self.analysis
        del self.data
        del self.file

    def upload_file(self, file, headers, unordered=False):
        if self.status in ['analysing', 'ready', 'processing']:
            raise Error('There is already a file being processed')
        encodings_to_try = ['utf-8', 'latin-1', 'utf-16', 'utf-32']
        file_data = None

        for encoding in encodings_to_try:
            try:
                # Seek to the beginning of the file before attempting decoding
                file.seek(0)
                file_data = file.read().decode(encoding)
                break  # Break out of loop if decoding succeeds
            except UnicodeDecodeError:
                continue  # Try the next encoding if decoding fails

        if file_data is None:
            raise Error('Invalid file type. Please upload a text file.')
        
        if not file_data:
            raise Error('The file is empty.')
        
        self.file = file_data
        self.has_headers = 'true' if headers else 'false'
        self.unordered = 'true' if unordered else 'false'
        self.status = 'analysing'
        
        # Initialize progress tracking
        self.analysis_progress = {'current': 0, 'total': 0, 'phase': 'Starting analysis...'}
        self.processing_progress = {'current': 0, 'total': 0, 'phase': 'Waiting for analysis...'}
        
        self.analysis_task_id = self.analysis_task.delay(self.uuid).id

    def read_csv_file(self, delimiter=None, quotechar=None):
        """
        Read CSV file with automatic delimiter and quote character detection.
        
        Args:
            delimiter (str, optional): Explicit delimiter to use. If None, will auto-detect.
            quotechar (str, optional): Explicit quote character to use. If None, will auto-detect.
        
        Returns:
            iterator: CSV rows as lists
        """
        io_string = io.StringIO(self.file)
        
        # Auto-detect delimiter and quote character if not provided
        if delimiter is None or quotechar is None:
            delimiter, quotechar = self._detect_csv_format_from_header(io_string)
        
        # Reset the StringIO object for reading
        io_string.seek(0)
        
        iterable = csv.reader(io_string, delimiter=delimiter, quotechar=quotechar)
        iterable = iter(self.clean_list(iterable))
        if self.has_headers == 'true':
            self.headers = next(iterable)
        return iterable

    def _detect_csv_format_from_header(self, io_string):
        """
        Automatically detect CSV delimiter and quote character by analyzing only the first line.
        
        Returns:
            tuple: (delimiter, quotechar)
        """
        # Common delimiters and quote characters
        delimiters = [',', ';', '\t', '|', ':']
        quote_chars = ['"', "'", None]
        
        # Read only the first line for analysis
        first_line = io_string.readline().strip()
        
        # Reset for later use
        io_string.seek(0)
        
        if not first_line:
            return ',', '"'  # Default fallback
        
        # Count occurrences of each delimiter in the header
        delimiter_counts = {}
        for delimiter in delimiters:
            count = first_line.count(delimiter)
            delimiter_counts[delimiter] = count
        
        # Find the most common delimiter
        detected_delimiter = max(delimiter_counts.items(), key=lambda x: x[1])[0]
        
        # If no clear delimiter found, default to comma
        if delimiter_counts[detected_delimiter] == 0:
            detected_delimiter = ','
        
        # Detect quote character by looking for balanced quotes in header
        detected_quotechar = '"'  # Default
        for quotechar in quote_chars:
            if quotechar is None:
                continue
            # Check if quotes are balanced in the header
            quote_count = first_line.count(quotechar)
            if quote_count > 0 and quote_count % 2 == 0:
                detected_quotechar = quotechar
                break
        
        return detected_delimiter, detected_quotechar

    def complete_analysis(self, analysis, data):
        del self.file
        self.status = 'ready'
        self.analysis = analysis
        self.data = data
        self.analysis_progress = {'current': 100, 'total': 100, 'phase': 'Analysis complete'}
        self.processing_progress = {'current': 0, 'total': len(data), 'phase': 'Ready to process'}

    def complete_processing(self):
        del self.analysis
        self.status = 'completed'
        self.processing_progress = {'current': 100, 'total': 100, 'phase': 'Processing complete'}

    def update_analysis_progress(self, current, total, phase=None):
        """Update analysis progress"""
        progress = {'current': current, 'total': total}
        if phase:
            progress['phase'] = phase
        else:
            progress['phase'] = f'Analyzing {current}/{total} rows...'
        self.analysis_progress = progress

    def update_processing_progress(self, current, total, phase=None):
        """Update processing progress"""
        progress = {'current': current, 'total': total}
        if phase:
            progress['phase'] = phase
        else:
            progress['phase'] = f'Processing {current}/{total} rows...'
        self.processing_progress = progress
    
    def append_processing_error(self, msg, line):
        msg = f'Line {line}: {msg}'
        if not self.processing_errors:
            self.processing_errors = [msg]
        else:
            self.processing_errors += [msg]

    def clean_list(self, lines):
        return [[self.clean_string(value) for value in line] for line in lines]

    def clean_string(self, input_string):
        # This removes non-printable characters sometimes found in CSVs
        return ''.join(char for char in input_string if 32 <= ord(char) <= 126)
