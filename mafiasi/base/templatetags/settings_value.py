from django import template
from django.conf import settings

from django.template import TemplateSyntaxError, Variable, Node, Variable, Library
register = template.Library()

ALLOWABLE_VALUES = (
    "REGISTER_ENABLED",
    "MAIL_SIGNATURE",
    "PROJECT_NAME",
    "PROJECT_BANNER",
    "MAIL_GREETING",
    "MAIL_INCLUDE_GERMAN",
    "MAIL_GREETING_DE",
    "MAIL_GREETING_EN",
)

register = Library()
# I found some tricks in URLNode and url from defaulttags.py:
# https://code.djangoproject.com/browser/django/trunk/django/template/defaulttags.py
@register.tag
def value_from_settings(parser, token):
  bits = token.split_contents()
  if len(bits) < 2:
    raise TemplateSyntaxError("'%s' takes at least one " \
      "argument (settings constant to retrieve)" % bits[0])
  settingsvar = bits[1]
  settingsvar = settingsvar[1:-1] if settingsvar[0] == '"' else settingsvar
  asvar = None
  bits = bits[2:]
  if len(bits) >= 2 and bits[-2] == 'as':
    asvar = bits[-1]
    bits = bits[:-2]
  if len(bits):
    raise TemplateSyntaxError("'value_from_settings' didn't recognise " \
      "the arguments '%s'" % ", ".join(bits))
  if settingsvar not in ALLOWABLE_VALUES:
      raise TemplateSyntaxError("The settings Variable %s is not allowed to be acessed" % settingsvar)
  return ValueFromSettings(settingsvar, asvar)

class ValueFromSettings(Node):
  def __init__(self, settingsvar, asvar):
    self.arg = Variable(settingsvar)
    self.asvar = asvar
  def render(self, context):
    ret_val = getattr(settings,str(self.arg))
    if self.asvar:
      context[self.asvar] = ret_val
      return ''
    else:
      return ret_val