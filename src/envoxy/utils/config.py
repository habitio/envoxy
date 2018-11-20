import uwsgi

class Config:

    @staticmethod
    def get(_node):
        return uwsgi.opts.get(_node, {})