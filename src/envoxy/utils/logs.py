try:
    import uwsgi
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

    class DefaultLog:
        def log(self, text):
            logger.debug(text)

        @property
        def opt(self):
            return {
                'log-level': Log.VERBOSE
            }

    uwsgi = DefaultLog()

from .datetime import Now
import socket
import os
import multiprocessing
from inspect import getframeinfo, stack
from .config import Config

_host = socket.gethostname()

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
    def generate(styles):
        return '\033[{}m'.format(styles if not isinstance(styles, list) else ';'.join(styles))
    
    @staticmethod
    def apply(text, styles=DEFAULT_FG):

        if text is not None:
            return ''.join([LogStyle.generate(styles), text, LogStyle.generate(LogStyle.RESET)])
        
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
    FORMAT = "json"

    style = LogStyle

    @staticmethod
    def truncate_text(text, max_lines=None):
        if max_lines is None:
            return text

        if isinstance(text, str):
            _lines_splitted = text.split('\n')

        elif isinstance(text, list):
            _lines_splitted = text

        else:
            return text
    
        _lines_count = len(_lines_splitted)

        if _lines_count > max_lines:
            
            _half_max_size = int(max_lines / 2)

            _text_list = []

            _text_list.extend(_lines_splitted[0:_half_max_size])
            _text_list.append('--- truncated ---')
            _text_list.extend(_lines_splitted[_lines_count-_half_max_size:])

            return ' '.join(_text_list)
        
        else:

            return text

    @staticmethod
    def log_level():
        return uwsgi.opt.get('log-level', Log.DEFAULT)

    @staticmethod
    def is_gte_log_level(log_level):
        return uwsgi.opt.get('log-level', Log.DEFAULT) >= log_level

    @staticmethod
    def is_format_log_pretty():
        return uwsgi.opt.get('log-format', Log.FORMAT) == "pretty"

    @staticmethod
    def emergency(text, max_lines=None):

        if Log.is_gte_log_level(Log.EMERGENCY):
            caller = getframeinfo(stack()[1][0])
            uwsgi.log(
                Log.format_log(
                '{} | {} | {}'.format(
                    LogStyle.apply(' emergency ', [LogStyle.RED_BG, LogStyle.WHITE_FG]),
                    LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                    Log.truncate_text(text, max_lines))
                , Log.EMERGENCY, caller)
            )

    @staticmethod
    def alert(text, max_lines=None):
        
        if Log.is_gte_log_level(Log.ALERT):
            caller = getframeinfo(stack()[1][0])
            uwsgi.log(
                Log.format_log(Log.truncate_text(text, max_lines), Log.ALERT, caller)
            )
    
    @staticmethod
    def critical(text, max_lines=None):
        
        if Log.is_gte_log_level(Log.CRITICAL):
            caller = getframeinfo(stack()[1][0])
            uwsgi.log(
                Log.format_log(Log.truncate_text(text, max_lines), Log.CRITICAL, caller)
            )

    @staticmethod
    def error(text, max_lines=None):
        
        if Log.is_gte_log_level(Log.ERROR):
            caller = getframeinfo(stack()[1][0])
            uwsgi.log(
                Log.format_log(Log.truncate_text(text, max_lines), Log.ERROR, caller)
            )

    @staticmethod
    def warning(text, max_lines=None):
        caller = getframeinfo(stack()[1][0])
        if Log.is_gte_log_level(Log.WARNING):
            uwsgi.log(
                Log.format_log(Log.truncate_text(text, max_lines), Log.WARNING, caller)
            )

    @staticmethod
    def notice(text, max_lines=100):
        
        if Log.is_gte_log_level(Log.NOTICE):
            caller = getframeinfo(stack()[1][0])
            uwsgi.log(
                Log.format_log(Log.truncate_text(text, max_lines), Log.NOTICE, caller)
            )

    @staticmethod
    def info(text, max_lines=100):
        
        if Log.is_gte_log_level(Log.INFO):
            caller = getframeinfo(stack()[1][0])
            uwsgi.log(
                Log.format_log(Log.truncate_text(text, max_lines), Log.INFO, caller)
            )

    @staticmethod
    def debug(text, max_lines=100):
        
        if Log.is_gte_log_level(Log.DEBUG):
            caller = getframeinfo(stack()[1][0])
            uwsgi.log(
                Log.format_log(Log.truncate_text(text, max_lines), Log.DEBUG, caller)
            )

    @staticmethod
    def trace(text, max_lines=100):
        
        if Log.is_gte_log_level(Log.TRACE):
            caller = getframeinfo(stack()[1][0])
            uwsgi.log(
                Log.format_log(Log.truncate_text(text, max_lines), Log.TRACE, caller)
            )

    @staticmethod
    def verbose(text, prefix=True, max_lines=None):
        
        if Log.is_gte_log_level(Log.VERBOSE):
            caller = getframeinfo(stack()[1][0])
            if prefix:
                uwsgi.log(
                    Log.format_log(Log.truncate_text(text, max_lines), Log.VERBOSE, caller)
                )
            else:
                uwsgi.log(
                    Log.format_log(str(Log.truncate_text(text, max_lines)), Log.VERBOSE, caller)
                )

    @staticmethod
    def system(text, max_lines=None):
        uwsgi.log(Log.truncate_text(text, max_lines))


    @staticmethod
    def format_log(text, log_level, caller):
        _level = int.from_bytes(log_level, 'little')
        _file = '.'.join(caller.filename.split('/')[-3:])
        text = str(text).replace('\"', '\\"').replace('\n', '\\n')
        _exec_name = Config.get('boot')[0]["name"] if Config and len(Config.get('boot')) else multiprocessing.current_process().name

        return f'{{ "version": "1.1", "host": "{_host}", "source": "{_host}", "short_message": "{text}" , "timestamp": {Now.timestamp()}, "level": {_level}, "pid": {os.getpid()}, "exec": "{_exec_name}", "file": "{_file}", "line": {caller.lineno}}}'
