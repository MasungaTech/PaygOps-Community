import sys
import inspect


class PrettyTraceBackService:

    @classmethod
    def get_pretty_trace_object(cls, exc_info):
        if not exc_info:
            exc_info = sys.exc_info()
        if not exc_info:
            return '' # No pretty traceback to get in that case
        
        traceback = []
        tb = exc_info[2]

        while tb:
            frame = tb.tb_frame
            frame_data = cls._get_frame(frame)
            if frame_data:
                traceback.append(frame_data)
            tb = tb.tb_next
        return traceback
    
    @classmethod
    def _get_frame(cls, frame, context_size_before=7, context_size_after=3):
        filepath = inspect.getfile(frame)
        if cls._is_excluded(filepath):
            return None
        fileline = frame.f_lineno
        try:
            locals = str(frame.f_locals)
        except Exception as e:
            locals = {'locals_not_available_reason': str(e)}
        return {
            'file': filepath, 
            'line': fileline,
            'fn_name': frame.f_code.co_name,
            'locals': locals,
            'code_start': fileline-context_size_before,
            'code': cls._get_relevant_lines(filepath, fileline, context_size_before, context_size_after)
        }
    
    @classmethod
    def _get_relevant_lines(cls, filepath, fileline, context_size_before, context_size_after):
        try:
            code_file = open(filepath, 'r')
            lines = code_file.readlines()
            return lines[fileline-context_size_before:fileline+context_size_after]
        except Exception as e:
            print('Issue getting code: '+str(e))
        return []

    @classmethod
    def _is_excluded(cls, filename):
        EXCLUDED_PATHS = ['site-packages/flask', '<string>', 'site-packages/celery', 'site-packages/click']
        for excl in EXCLUDED_PATHS:
            if excl in filename:
                return True
        return False