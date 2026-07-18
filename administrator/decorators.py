from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required


def role_required(*allowed_roles):
    """
    Decorator untuk membatasi akses view berdasarkan role user.
    Contoh: @role_required('petugas')
            @role_required('administrator', 'petugas')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in allowed_roles:
                raise PermissionDenied("Anda tidak memiliki akses ke halaman ini.")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator