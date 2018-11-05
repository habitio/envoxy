from .utils import Utils
from .views.containers import Response

def event_wrapper(_object):
    return Response(_object).to_flask()