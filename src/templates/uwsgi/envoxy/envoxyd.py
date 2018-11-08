import sys
import os
import json
import uwsgi
import inspect

import importlib.util

from flask import Flask

sys.path.append("/opt/envoxy")

import envoxy

app = Flask(__name__)
app.response_class = envoxy.Response

app.debug = True

if 'mode' in uwsgi.opt and uwsgi.opt['mode'] == b'test':
    
    @app.route('/')
    def index():
        return "ENVOXY Working!"

elif 'conf' in uwsgi.opt:
    
    _conf_path = uwsgi.opt['conf'].decode('utf-8')
    
    envoxy.log.system('[{}] Configuration file param found: {}\n'.format(
        envoxy.log.style.apply('OK', envoxy.log.style.GREEN_FG),
        _conf_path
    ))
    
    if os.path.exists(_conf_path) and os.path.isfile(_conf_path):

        envoxy.log.system('[{}] Configuration file exists! Trying to parse the file...\n'.format(
            envoxy.log.style.apply('---', envoxy.log.style.BLUE_FG)
        ))

        _module_name = os.path.basename(_conf_path).replace('.json', '')

        # try:
        _conf_file = open(_conf_path, encoding='utf-8')
        _conf_content = json.loads(_conf_file.read(), encoding='utf-8')
        envoxy.log.system('[{}] The configuration file was parsed successfully!\n\n'.format(
            envoxy.log.style.apply('OK', envoxy.log.style.GREEN_FG)
        ))

        _log_conf = _conf_content.get('log')

        if _log_conf and _log_conf.get('level'):
            uwsgi.opt['log-level'] = bytes([_log_conf['level']])

        _modules_list = _conf_content.get('modules')

        for _module_path in _modules_list:

            envoxy.log.system('[{}] Module path: {}\n'.format(
                envoxy.log.style.apply('MMM', envoxy.log.style.BLUE_FG),
                _module_path
            ))

            #try:
    
            _spec = importlib.util.spec_from_file_location('__init__', _module_path)
            _module = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_module)

            for _name, _obj in inspect.getmembers(_module):
                
                if _name == '__loader__' and isinstance(_obj, list) and len(_obj)>0:

                    envoxy.log.system('[{}] Loader: {}\n'.format(
                        envoxy.log.style.apply('...', envoxy.log.style.BLUE_FG), 
                        _obj
                    ))
        
                    for _view_class in _obj:
                        _instance = _view_class()
                        _instance.set_flask(app)
                        uwsgi.log('\n')
                        envoxy.log.system('[{}] Loaded "{}".\n'.format(
                            envoxy.log.style.apply('###', envoxy.log.style.BLUE_FG),
                            str(_view_class)
                        ))

                # except Exception as _ex:

                #     print("*** Exception when module class was called: {}".format(_ex))
                #     exit(-1)


        # except Exception as e:
        #     print('*** An error was thrown when ENVOXY tried to parse the file: {}\n\n'.format(e))
        #     exit(-1)

    else:

        envoxy.log.emergency('Configuration file not found in this path! Please check if the file exists or the permissions are enough.\n\n')
        exit(-10)



else:
    envoxy.log.emergency('Configuration file not found! Please use ./envoxy [params] --set conf=<file> or ./envoxy [params] --set mode=test\n\n')
    exit(-10)

uwsgi.log('\n\n')