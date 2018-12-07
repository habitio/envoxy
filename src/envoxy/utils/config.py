import uwsgi

class Config:

    @staticmethod
    def get(node):
        return uwsgi.opt.get('conf_content', {}).get(node, {})