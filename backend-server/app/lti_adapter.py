from pylti1p3.request import Request

class FastAPIRequestAdapter(Request):
    def __init__(self, request, form_data=None):
        self.request = request
        self.form_data = form_data or {}
        
    def get_param(self, key):
        if key in self.form_data:
            return self.form_data.get(key)
        return self.request.query_params.get(key)
        
    def get_cookie(self, key):
        return self.request.cookies.get(key)
        
    @property
    def is_secure(self):
        # Depending on proxy, often behind http
        return True
        
    def get_url(self):
        return str(self.request.url)
        
    def get_session(self):
        # Pylti1p3 expects a session dict. FastAPI doesn't have standard session.
        # This will be tricky, normally we implement a simple session or mock.
        return {}
