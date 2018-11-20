import uwsgi

from datetime import datetime

class Now:

    @staticmethod
    def log_format():
        return datetime.now().utcnow().strftime('%Y-%m-%dT%H:%M:%S')


class LogStyle:

    # Reset
    RESET = '0'
    
    # Decorations
    BOLD = '1'
    UNDERLINE = '4'

    # Foreground Colors
    DEFAULT_FG = '39'
    BLACK_FG = '30'
    RED_FG = '31'
    GREEN_FG = '32'
    YELLOW_FG = '33'
    BLUE_FG = '34'
    MAGENTA_FG = '35'
    CYAN_FG = '36'
    LGRAY_FG = '37'
    DGRAY_FG = '90'
    LRED_FG = '91'
    LGREEN_FG = '92'
    LYELLOW_FG = '93'
    LBLUE_FG = '94'
    LMAGENTA_FG = '95'
    LCYAN_FG = '96'
    WHITE_FG = '97'

    # Background colors
    DEFAULT_BG = '49'
    BLACK_BG = '40'	
    RED_BG = '41'
    GREEN_BG = '42'
    YELLOW_BG = '43'
    BLUE_BG = '44'
    MAGENTA_BG = '45'
    CYAN_BG = '46'
    LGRAY_BG = '47'
    DGRAY_BG = '100'
    LRED_BG = '101'
    LGREEN_BG = '102'
    LYELLOW_BG = '103'
    LBLUE_BG = '104'
    LMAGENTA_BG = '105'
    LCYAN_BG = '106'
    WHITE_BG = '107'
    
    # Patterns
    EMERGENCY = '4;31'
    ALERT = '4;31'
    CRITICAL = '4;35'
    ERROR = '4;35'
    WARNING = '4;35'
    NOTICE = '4;36'
    INFO = '4;37'
    DEBUG = '4;33'
    TRACE = '4;32'
    VERBOSE = '4;32'

    @staticmethod
    def generate(_styles):
        return '\033[{}m'.format(_styles if not isinstance(_styles, list) else ';'.join(_styles))
    
    @staticmethod
    def apply(_text, _styles=DEFAULT_FG):

        if _text is not None:
            return ''.join([LogStyle.generate(_styles), _text, LogStyle.generate(LogStyle.RESET)])
        
        return None

class Log:

    EMERGENCY = b'\x00'
    ALERT = b'\x01'
    CRITICAL = b'\x02'
    ERROR = b'\x03'
    WARNING = b'\x04'
    NOTICE = b'\x05'
    INFO = b'\x06'
    DEBUG = b'\x07'
    TRACE = b'\x08'
    VERBOSE = b'\x09'

    DEFAULT = EMERGENCY

    style = LogStyle

    @staticmethod
    def is_gte_log_level(_log_level):
        return uwsgi.opt.get('log-level', Log.DEFAULT) >= _log_level

    @staticmethod
    def emergency(_text):

        if Log.is_gte_log_level(Log.EMERGENCY):
        
            uwsgi.log('{} | {} | {}'.format(
                LogStyle.apply(' emergency ', [LogStyle.RED_BG, LogStyle.WHITE_FG]),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def alert(_text):
        
        if Log.is_gte_log_level(Log.ALERT):
        
            uwsgi.log('{} | {} | {}'.format(
                LogStyle.apply('   alert   ', LogStyle.ALERT),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))
    
    @staticmethod
    def critical(_text):
        
        if Log.is_gte_log_level(Log.CRITICAL):
        
            uwsgi.log('{} | {} | {}'.format(
                LogStyle.apply(' critical  ', LogStyle.CRITICAL),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def error(_text):
        
        if Log.is_gte_log_level(Log.ERROR):
        
            uwsgi.log('{} | {} | {}'.format(
                LogStyle.apply('   error   ', LogStyle.ERROR),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def warning(_text):

        if Log.is_gte_log_level(Log.WARNING):
    
            uwsgi.log('{} | {} | {}'.format(
                LogStyle.apply('  warning  ', LogStyle.WARNING),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def notice(_text):
        
        if Log.is_gte_log_level(Log.NOTICE):
        
            uwsgi.log('{} | {} | {}'.format(
                LogStyle.apply('  notice   ', LogStyle.NOTICE),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def info(_text):
        
        if Log.is_gte_log_level(Log.INFO):
        
            uwsgi.log('{} | {} | {}'.format(
                LogStyle.apply('   info    ', LogStyle.INFO),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def debug(_text):
        
        if Log.is_gte_log_level(Log.DEBUG):
        
            uwsgi.log('{} | {} | {}'.format(
                LogStyle.apply('   debug   ', LogStyle.DEBUG),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def trace(_text):
        
        if Log.is_gte_log_level(Log.TRACE):
        
            uwsgi.log('{} | {} | {}'.format(
                LogStyle.apply('   trace   ', LogStyle.TRACE),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def verbose(_text, _prefix=True):
        
        if Log.is_gte_log_level(Log.VERBOSE):
        
            if _prefix:
                uwsgi.log('{} | {} | {}'.format(
                    LogStyle.apply('  verbose  ', LogStyle.VERBOSE),
                    LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                    _text
                ))
            else:
                uwsgi.log(str(_text))

    @staticmethod
    def system(_text):
        uwsgi.log(_text)