from datetime import datetime

class Now:

    @staticmethod
    def log_format():
        return datetime.now().utcnow().strftime('%Y-%m-%dT%H:%M:%S')

    @staticmethod
    def api_format():
        return '+'.join([datetime.now().utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3], '0000'])