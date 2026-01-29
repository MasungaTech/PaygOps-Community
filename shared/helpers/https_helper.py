

class ReverseProxied(object):
    """
    Because we are reverse proxied from a load balancer
    use environ/config to signal https
    since flask ignores preferred_url_scheme in url_for calls
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        forwarded_scheme = environ.get("HTTP_X_FORWARDED_PROTO", None)
        if "https" == forwarded_scheme:
            environ["wsgi.url_scheme"] = "https"
        return self.app(environ, start_response)
