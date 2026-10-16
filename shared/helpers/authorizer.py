from functools import wraps
from flask import redirect, url_for, flash, render_template
from flask_login import current_user
from pony.orm import db_session


class authorizer:
    def __init__(self, auth_key, redir_to_dest=None, flash_me=True, any=False, **keywargs):
        self.auth_key = auth_key
        self.redir_to_dest = redir_to_dest
        self.flash_me = flash_me
        self.any = any
        self.is_endpoint = keywargs.get('is_endpoint', False)

    def __call__(self, f):
        @wraps(f)
        def wrapped_func(*args, **kwargs):
            return self.can_access(f, *args, **kwargs)
        return wrapped_func

    def can_access(self, f, *args, **kwargs):
        with db_session:
            can_access = current_user.can_access_in_scope(self.auth_key)
            if not can_access:
                if self.flash_me:
                    flash("You do not have the permission required to access this page. Permission required: "+str(self.auth_key), category='error')
                if not self.redir_to_dest and self.is_endpoint:
                    return render_template('access_denied.html')
                if self.redir_to_dest is None:
                    return redirect(url_for('index'))
                return redirect(url_for(self.redir_to_dest))
        return f(*args, **kwargs)
