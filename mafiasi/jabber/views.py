from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from mafiasi.registration.forms import CheckPasswordForm
from mafiasi.jabber.models import get_account, create_account

def index(request):
    jabber_user = get_account(request.user)

    return TemplateResponse(request, 'jabber/index.html', {
        'jabber_user': jabber_user,
        'jabber_domain': settings.JABBER_DOMAIN,
        'cert_fingerprint': settings.JABBER_CERT_FINGERPRINT
    })

@login_required
def create(request):
    if get_account(request.user) is not None:
        return redirect('jabber_password_reset')
    
    if request.method == 'POST':
        form = CheckPasswordForm(request.POST, user=request.user)
        if form.is_valid():
            password = form.cleaned_data['password']
            status, user = create_account(request.user, password)
            if status == 'created':
                messages.success(request, _('Account was created.'))
            elif status == 'exists':
                messages.warning(request, _('Account already exists.'))
            else:
                messages.error(request, _('Sorry, we had an internal error.'))
            return redirect('jabber_index')
    else:
        form = CheckPasswordForm(user=request.user)

    return TemplateResponse(request, 'jabber/create.html', {
        'form': form
    })

@login_required
def password_reset(request):
    account = get_account(request.user)
    if account is None:
        return redirect('jabber_create')

    if request.method == 'POST':
        form = CheckPasswordForm(request.POST, user=request.user)
        if form.is_valid():
            password = form.cleaned_data['password']
            account.password = password
            account.save()
            messages.success(request, _("Password was changed."))
            return redirect('jabber_index')
    else:
        form = CheckPasswordForm(user=request.user)

    return TemplateResponse(request, 'jabber/password_reset.html', {
        'form': form
    })
