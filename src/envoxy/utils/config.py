import json

try:
    import uwsgi

    class Config:

        @staticmethod
        def get(node):
            return uwsgi.opt.get('conf_content', {}).get(node, {})

        @staticmethod
        def get_credentials():
            return uwsgi.opt.get('credentials', {})

        @staticmethod
        def plugins():
            return uwsgi.opt.get('plugins', {})

except:

    class Config:

        file_path = None

        @staticmethod
        def set_file_path(file_path):
            Config.file_path = file_path

        @staticmethod
        def get(node):

            _conf_content = {}

            if Config.file_path:
                _conf_file = open( Config.file_path, encoding='utf-8')
                _conf_content = json.loads(_conf_file.read(), encoding='utf-8')

            return _conf_content.get(node, {})

        @staticmethod
        def get_credentials():

            from ..auth.backends import authenticate_container as authenticate

            _auth_conf = Config.get('credentials')
            _credentials = authenticate(_auth_conf)

            return _credentials

        @staticmethod
        def plugins():
            return uwsgi.opt.get('plugins', {})



