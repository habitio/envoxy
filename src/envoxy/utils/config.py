import uwsgi

class Config:

    @staticmethod
    def get(_node):
        return uwsgi.opt.get('conf_content', {}).get(_node, {})