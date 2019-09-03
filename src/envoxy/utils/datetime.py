from datetime import datetime
import time

class Now:

    @staticmethod
    def log_format():
        return datetime.now().utcnow().strftime('%Y-%m-%dT%H:%M:%S')

    @staticmethod
    def api_format():
        return '+'.join([datetime.now().utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3], '0000'])

    @staticmethod
    def timestamp():
        return int(time.time())

    @staticmethod
    def to_datetime(date_str, format_str="%Y-%m-%dT%H:%M:%S.%f+0000"):
        try:
            return datetime.strptime(date_str, format_str)
        except:
            pass
