try:
    import uwsgi
except:
    pass

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


