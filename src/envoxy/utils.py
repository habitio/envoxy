import json
import uwsgi

from datetime import datetime

from requests import Response as RequestsResponse
from flask import Response as FlaskResponse

class Utils:

    @staticmethod
    def response_handler(response: RequestsResponse) -> FlaskResponse:
        try:
            return FlaskResponse(response.text, response.status_code, headers=response.headers.items())
        except Exception as e:
            return FlaskResponse({'text': e}, 500)


class Now:

    @staticmethod
    def log_format():
        return datetime.now().utcnow().strftime('%Y-%m-%dT%H:%M:%S')


class LogStyle:

    # Reset
    ENDC = '\033[0m'
    
    # Decorations
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    # Foreground Colors
    DEFAULT_FG = '\033[39m'
    BLACK_FG = '\033[30m'
    RED_FG = '\033[31m'
    GREEN_FG = '\033[32m'
    YELLOW_FG = '\033[33m'
    BLUE_FG = '\033[34m'
    MAGENTA_FG = '\033[35m'
    CYAN_FG = '\033[36m'
    LGRAY_FG = '\033[37m'
    DGRAY_FG = '\033[90m'
    LRED_FG = '\033[91m'
    LGREEN_FG = '\033[92m'
    LYELLOW_FG = '\033[93m'
    LBLUE_FG = '\033[94m'
    LMAGENTA_FG = '\033[95m'
    LCYAN_FG = '\033[96m'
    WHITE_FG = '\033[97m'

    # Background colors
    DEFAULT_BG = '\033[49m'
    BLACK_BG = '\033[40m'	
    RED_BG = '\033[41m'
    GREEN_BG = '\033[42m'
    YELLOW_BG = '\033[43m'
    BLUE_BG = '\033[44m'
    MAGENTA_BG = '\033[45m'
    CYAN_BG = '\033[46m'
    LGRAY_BG = '\033[47m'
    DGRAY_BG = '\033[100m'
    LRED_BG = '\033[101m'
    LGREEN_BG = '\033[102m'
    LYELLOW_BG = '\033[103m'
    LBLUE_BG = '\033[104m'
    LMAGENTA_BG = '\033[105m'
    LCYAN_BG = '\033[106m'
    WHITE_BG = '\033[107m'
    
    # Patterns
    EMERGENCY_FG = '\033[4;31m'
    ALERT_FG = '\033[4;31m'
    CRITICAL_FG = '\033[4;35m'
    ERROR_FG = '\033[4;35m'
    WARNING_FG = '\033[4;35m'
    NOTICE_FG = '\033[4;36m'
    INFO_FG = '\033[4;37m'
    DEBUG_FG = '\033[4;33m'
    TRACE_FG = '\033[4;32m'
    VERBOSE_FG = '\033[4;32m'
    
    @staticmethod
    def apply(_text, _style=DEFAULT_FG):

        if _text is not None:
            return ''.join([''.join(_style) if isinstance(_style, list) else _style, _text, LogStyle.ENDC])
        
        return None

class Log:

    style = LogStyle

    @staticmethod
    def emergency(_text):

        if uwsgi.opt.get('log-level', b'\x00') >= b'\x00':
        
            uwsgi.log(' {} | {} | {}'.format(
                LogStyle.apply(' emergency ', [LogStyle.RED_BG, LogStyle.WHITE_FG]),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def alert(_text):
        
        if uwsgi.opt.get('log-level', b'\x00') >= b'\x01':
        
            uwsgi.log(' {} | {} | {}'.format(
                LogStyle.apply('   alert   ', [LogStyle.UNDERLINE, LogStyle.ALERT_FG]),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))
    
    @staticmethod
    def critical(_text):
        
        if uwsgi.opt.get('log-level', b'\x00') >= b'\x02':
        
            uwsgi.log(' {} | {} | {}'.format(
                LogStyle.apply(' critical  ', [LogStyle.UNDERLINE, LogStyle.CRITICAL_FG]),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def error(_text):
        
        if uwsgi.opt.get('log-level', b'\x00') >= b'\x03':
        
            uwsgi.log(' {} | {} | {}'.format(
                LogStyle.apply('   error   ', [LogStyle.UNDERLINE, LogStyle.ERROR_FG]),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def warning(_text):

        if uwsgi.opt.get('log-level', b'\x00') >= b'\x04':
    
            uwsgi.log(' {} | {} | {}'.format(
                LogStyle.apply('  warning  ', [LogStyle.UNDERLINE, LogStyle.WARNING_FG]),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def notice(_text):
        
        if uwsgi.opt.get('log-level', b'\x00') >= b'\x05':
        
            uwsgi.log(' {} | {} | {}'.format(
                LogStyle.apply('  notice   ', [LogStyle.UNDERLINE, LogStyle.NOTICE_FG]),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def info(_text):
        
        if uwsgi.opt.get('log-level', b'\x00') >= b'\x06':
        
            uwsgi.log(' {} | {} | {}'.format(
                LogStyle.apply('   info    ', [LogStyle.UNDERLINE, LogStyle.INFO_FG]),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def debug(_text):
        
        if uwsgi.opt.get('log-level', b'\x00') >= b'\x07':
        
            uwsgi.log(' {} | {} | {}'.format(
                LogStyle.apply('   debug   ', [LogStyle.UNDERLINE, LogStyle.DEBUG_FG]),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def trace(_text):
        
        if uwsgi.opt.get('log-level', b'\x00') >= b'\x08':
        
            uwsgi.log(' {} | {} | {}'.format(
                LogStyle.apply('   trace   ', [LogStyle.UNDERLINE, LogStyle.TRACE_FG]),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def verbose(_text):
        
        if uwsgi.opt.get('log-level', b'\x00') >= b'\x09':
        
            uwsgi.log(' {} | {} | {}'.format(
                LogStyle.apply('  verbose  ', [LogStyle.UNDERLINE, LogStyle.VERBOSE_FG]),
                LogStyle.apply(Now.log_format(), LogStyle.BOLD),
                _text
            ))

    @staticmethod
    def system(_text):
        uwsgi.log(_text)