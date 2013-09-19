from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import MAXIMUM_PASSWORD_LENGTH

from mafiasi.base.models import Yeargroup

class RegisterForm(forms.Form):
    account = forms.CharField()


class AdditionalInfoForm(forms.Form):
    def __init__(self, *args, **kwargs):
        account = kwargs.pop('account')
        super(AdditionalInfoForm, self).__init__(*args, **kwargs)
        if account[0].isdigit():
            group_name = u'___{0}'.format(account[0])
            where = ["slug LIKE '{0}'".format(group_name)]
            yeargroups = Yeargroup.objects.extra(where=where)
        else:
            yeargroups = Yeargroup.objects.all()
        self.fields["yeargroup"] = forms.ModelChoiceField(
                queryset=yeargroups)
    
    first_name = forms.CharField(max_length=40)
    last_name = forms.CharField(max_length=40)


class PasswordForm(forms.Form):
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput,
        max_length=MAXIMUM_PASSWORD_LENGTH,
    )   
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput,
        max_length=MAXIMUM_PASSWORD_LENGTH,
    )   

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    _("The two password fields didn't match."))
        return password2
