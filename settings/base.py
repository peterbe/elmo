# Django settings file for a project based on the playdoh template.

import os

from django.utils.functional import lazy

# Make file paths relative to settings.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
path = lambda *a: os.path.join(ROOT, *a)

ROOT_PACKAGE = os.path.basename(ROOT)

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = ()
MANAGERS = ADMINS

DATABASES = {}  # See settings/local.py

# Site ID is used by Django's Sites framework.
SITE_ID = 1


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
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Gettext text domain
TEXT_DOMAIN = 'messages'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-US'

# Accepted locales
KNOWN_LANGUAGES = ('en-US',)

# List of RTL locales known to this project. Subset of LANGUAGES.
RTL_LANGUAGES = ()  # ('ar', 'fa', 'fa-IR', 'he')

LANGUAGE_URL_MAP = dict([(i.lower(), i) for i in KNOWN_LANGUAGES])

# Override Django's built-in with our native names
class LazyLangs(dict):
    def __new__(self):
        from product_details import product_details
        return dict([(lang.lower(), product_details.languages[lang]['native'])
                     for lang in KNOWN_LANGUAGES])

# Where to store product details etc.
PROD_DETAILS_DIR = path('lib/product_details_json')

LANGUAGES = lazy(LazyLangs, dict)()

# Paths that don't require a locale code in the URL.
SUPPORTED_NONLOCALES = []


## Media and templates.

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = path('static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '1iz#v0m55@h26^m6hxk3a7at*h$qj_2a$juu1#nv50548j(x1v'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.csrf',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages',
    'commons.context_processors.i18n',
    'accounts.context_processors.accounts',
)

TEMPLATE_DIRS = (
    path('templates'),
)

def JINJA_CONFIG():
    import jinja2
    from django.conf import settings
#    from caching.base import cache
    config = {'extensions': ['tower.template.i18n', 'jinja2.ext.do',
                             'jinja2.ext.with_', 'jinja2.ext.loopcontrols'],
              'finalize': lambda x: x if x is not None else ''}
#    if 'memcached' in cache.scheme and not settings.DEBUG:
        # We're passing the _cache object directly to jinja because
        # Django can't store binary directly; it enforces unicode on it.
        # Details: http://jinja.pocoo.org/2/documentation/api#bytecode-cache
        # and in the errors you get when you try it the other way.
#        bc = jinja2.MemcachedBytecodeCache(cache._cache,
#                                           "%sj2:" % settings.CACHE_PREFIX)
#        config['cache_size'] = -1 # Never clear the cache
#        config['bytecode_cache'] = bc
    return config

# This is the common prefix displayed in front of ALL static files
STATIC_URL = '/static/'

# the location where all collected files end up.
# the reason for repeated the word 'static' inside 'collected/'
# is so we, in nginx/apache, can set up the root to be
# <base path>/collected
# then a URL like http://domain/static/js/jquery.js just works
STATIC_ROOT = path('collected', 'static')

## Middlewares, apps, URL configs.

MIDDLEWARE_CLASSES = (
    # Commented out because at the moment elmo doesn't localize templates
    # and middleware don't work when views use render_to_reponse() without
    # a RequestContext(request) passed along.
    #'commons.middleware.LocaleURLMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    'commonware.middleware.FrameOptionsHeader',
    'commonware.middleware.HidePasswordOnException',

    'django_arecibo.middleware.AreciboMiddleware',
)

ROOT_URLCONF = '%s.urls' % ROOT_PACKAGE

INSTALLED_APPS = (
    # Local apps
    'commons',  # Content common to most playdoh-based apps.
    'tower',  # for ./manage.py extract (L10n)
    'nashvegas',
    'django_arecibo',
    'compressor',

    # We need this so the jsi18n view will pick up our locale directory.
    ROOT_PACKAGE,

    # Third-party apps
    'commonware.response.cookies',
    'djcelery',
    'django_nose',

    # Django contrib apps
    'django.contrib.auth',
    'django_sha2',  # Load after auth to monkey-patch it.

    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    # L10n
    'product_details',

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

)

# Tells the extract script what files to look for L10n in and what function
# handles the extraction. The Tower library expects this.
DOMAIN_METHODS = {
    'messages': [
        ('apps/**.py',
            'tower.management.commands.extract.extract_tower_python'),
        ('**/templates/**.html',
            'tower.management.commands.extract.extract_tower_template'),
    ],

    ## Use this if you have localizable HTML files:
    #'lhtml': [
    #    ('**/templates/**.lhtml',
    #        'tower.management.commands.extract.extract_tower_template'),
    #],

    ## Use this if you have localizable JS files:
    #'javascript': [
        # Make sure that this won't pull in strings from external libraries you
        # may use.
    #    ('media/js/**.js', 'javascript'),
    #],
}

# Path to Java. Used for compress_assets.
JAVA_BIN = '/usr/bin/java'

## Auth
PWD_ALGORITHM = 'bcrypt'
HMAC_KEYS = {
    '2011-04-12': 'anything?',
}

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

## Tests
#TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'
TEST_RUNNER = 'test_utils.runner.RadicalTestSuiteRunner' # same as playdoh

## Arecibo
# See http://readthedocs.org/docs/mozweb/en/latest/errors.html
ARECIBO_PUBLIC_ACCOUNT_NUMBER = ""  # not needed behind firewall
ARECIBO_SERVER_URL = ""

ARECIBO_SETTINGS = {
    'EXCLUDED_POST_VARS': ['password',],
}

## Celery
# commented out because it's not being used
#BROKER_HOST = 'localhost'
#BROKER_PORT = 5672
#BROKER_USER = 'playdoh'
#BROKER_PASSWORD = 'playdoh'
#BROKER_VHOST = 'playdoh'
#BROKER_CONNECTION_TIMEOUT = 0.1
#CELERY_RESULT_BACKEND = 'amqp'
#CELERY_IGNORE_RESULT = True

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
