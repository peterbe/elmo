# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Django settings file for a project based on the playdoh template.

from funfactory.settings_base import *

from django.utils.functional import lazy

DEBUG = TEMPLATE_DEBUG = False

# because we're not using the pythonic structure as per funfactory
ROOT_PACKAGE = os.path.basename(ROOT)

ADMINS = ()
MANAGERS = ADMINS

DATABASES = {}  # See settings/local.py

## Internationalization.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
#USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
#USE_L10N = True


## Media and templates.

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS += (
    'django.core.context_processors.static',
    'accounts.context_processors.accounts',
    'homepage.context_processors.analytics',
)

# This is the common prefix displayed in front of ALL static files
STATIC_URL = '/static/'


# the location where all collected files end up.
# the reason for repeated the word 'static' inside 'collected/'
# is so we, in nginx/apache, can set up the root to be
# <base path>/collected
# then a URL like http://domain/static/js/jquery.js just works
STATIC_ROOT = COMPRESS_ROOT = path('collected', 'static')

## Middlewares, apps, URL configs.

# not using funfactory.settings_base.MIDDLEWARE_CLASSES here because there's
# so few things we need and so many things we'd need to add
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'session_csrf.CsrfMiddleware',

    'commonware.middleware.FrameOptionsHeader',
    'commonware.middleware.ScrubRequestOnException',

    'django_arecibo.middleware.AreciboMiddleware',
)

INSTALLED_APPS += (
    ROOT_PACKAGE,

    # Local apps
    'commons',
    'nashvegas',
    'django_arecibo',
    'compressor',

    # Third-party apps
    'django_qunit',

    # Django contrib apps
    'django.contrib.staticfiles',
    'django.contrib.admin',

    # L10n

    # elmo specific
    'accounts',
    'homepage',
    'privacy',
    'life',
    'mbdb',
    'pushes',
    'dashtags',
    'l10nstats',
    'tinder',
    'shipping',
    'bugsy',
    'webby',
    'elmo_commons',

)


## Auth
PWD_ALGORITHM = 'bcrypt'
HMAC_KEYS = {
    '2012-10-23': 'something',
}

from django_sha2 import get_password_hashers
PASSWORD_HASHERS = get_password_hashers(BASE_PASSWORD_HASHERS, HMAC_KEYS)

SESSION_COOKIE_SECURE = True

## Tests

## Arecibo
# See http://readthedocs.org/docs/mozweb/en/latest/errors.html
ARECIBO_PUBLIC_ACCOUNT_NUMBER = ""  # not needed behind firewall
ARECIBO_SERVER_URL = ""
ARECIBO_USES_CELERY = False
ARECIBO_SETTINGS = {
    'EXCLUDED_POST_VARS': ['password',],
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',  # fox2mike suggest to use IP instead of localhost
        'TIMEOUT': 500,
        'KEY_PREFIX': 'elmo',
    }
}

# When we have a good cache backend, we can get much faster session storage
# using the cache backend
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

## django_compressor
COMPRESS_ENABLED = True  # defaults to `not DEBUG`
COMPRESS_OFFLINE = True  # make sure you run `./manage.py compress` upon deployment
COMPRESS_CSS_FILTERS = (
  'compressor.filters.css_default.CssAbsoluteFilter',
  'compressor.filters.cssmin.CSSMinFilter',
)
COMPRESS_JS_FILTERS = (
  'filters.void_js_filter.VoidJSFilter',
)
STATICFILES_FINDERS = (
  'django.contrib.staticfiles.finders.FileSystemFinder',
  'django.contrib.staticfiles.finders.AppDirectoriesFinder',
  'compressor.finders.CompressorFinder',
)

## Feeds
L10N_FEED_URL = 'http://planet.mozilla.org/l10n/atom.xml'
HOMEPAGE_FEED_SIZE = 5

## Google Analytics
INCLUDE_ANALYTICS = False

# QUnit testing
QUNIT_TEST_DIRECTORY = path('static/tests')


try:
    import ldap_settings
except ImportError:
    import warnings
    warnings.warn("ldap_settings not importable. No LDAP authentication")
else:
    # all these must exist and be set to something
    for each in 'LDAP_HOST', 'LDAP_DN', 'LDAP_PASSWORD':
        if not getattr(ldap_settings, each, None):
            raise ValueError('%s must be set' % each)

    from ldap_settings import *
    # ImportErrors are not acceptable if ldap_loaded is True
    import ldap
    MIDDLEWARE_CLASSES = (MIDDLEWARE_CLASSES +
      ('django.contrib.auth.middleware.RemoteUserMiddleware',))
    AUTHENTICATION_BACKENDS = ('lib.auth.backends.MozLdapBackend',)

WEBDASHBOARD_URL = 'https://l10n.mozilla-community.org/webdashboard/'

## Verbatim bridging
# codes that map to `None` deliberately don't exist on Verbatim
VERBATIM_CONVERSIONS = {
    'en-US': None,
    'es-ES': 'es',
    'fy-NL': 'fy',
    'ga-IE': 'ga',
    'ja-JP-mac': 'ja',
    'nr': None,
    'pa-IN': 'pa',
    'pt-PT': 'pt',
    'rw': None,
    'ss': None,
    'sv-SE': 'sv',
    'tn': None,
    'ts': None,
    've': None,
    'x-testing': None,
    'xh': None,
    'zu': None,
}
