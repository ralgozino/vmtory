from django.utils.translation import ugettext_lazy as _

"""
Django settings for vminventory project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'wun$ty%5f92!r9@r=*05!id)!#leeb4u!tit=x1ib*cvh0yih6'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Set this list of users and e-mails addresses if you want to get e-mails when something goes wrong.
#ADMINS = [('Name Lastname', 'em@ail')]

# Set the hostname that should serve this app. See:
# https://docs.djangoproject.com/en/2.2/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': os.path.join(BASE_DIR, 'templates'),
        'APP_DIRS': True,
        # 'DEBUG': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                # 'django.core.context_processors.request',
            ],
        },
    },
]
#TEMPLATE_CONTEXT_PROCESSORS =  (
    #'django.core.context_processors.request',
    #'django.contrib.auth.context_processors.auth',
#)

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'vmtory',
    'django_tables2',
    'django_python3_ldap',
    'crispy_forms',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'vminventory.urls'

WSGI_APPLICATION = 'vminventory.wsgi.application'

AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',
                           # Uncomment the following line fot LDAP auth
                           # 'django_python3_ldap.auth.LDAPBackend',
                           )
# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        #'ENGINE': 'django.db.backends.sqlite3',
        #'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'vmtory',
        'USER': 'django',
        'PASSWORD': 'django',
        'HOST': 'db',
    }
    
}

# We use this backend that prints all the emails in console instead of sending them
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# EMAIL_HOST = '<your mail server>'
# EMAIL_PORT = '25'

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGES = (
    ('en', _('English')),
    ('es', _('Spanish')),
    )
#LANGUAGE_CODE = 'es-AR'
LANGUAGE_CODE = 'en'
TIME_ZONE = 'America/Argentina/Cordoba'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
# STATIC_ROOT = '/home/administrator/vmtory/vminventory/vmtory/static/'

# Theme para los formularios crispy
CRISPY_TEMPLATE_PACK = 'uni_form'

# LDAP Configuration
# The URL of the LDAP server.
# LDAP_AUTH_URL = "ldap://ldapserver.yourdomain:389"

# Initiate TLS on connection.
# LDAP_AUTH_USE_TLS = False

# The LDAP search base for looking up users.
# LDAP_AUTH_SEARCH_BASE = "ou=Users,dc=yourcomany,dc=com,dc=ar"

# The LDAP class that represents a user.
# LDAP_AUTH_OBJECT_CLASS = "posixAccount"

# User model fields mapped to the LDAP
# attributes that represent them.
# LDAP_AUTH_USER_FIELDS = {
#     "username": "uid",
#     "first_name": "givenName",
#     "last_name": "sn",
#     "email": "mail",
# }

# A tuple of django model fields used to uniquely identify a user.
# LDAP_AUTH_USER_LOOKUP_FIELDS = ("username",)

# Path to a callable that takes a dict of {model_field_name: value},
# returning a dict of clean model data.
# Use this to customize how data loaded from LDAP is saved to the User model.
LDAP_AUTH_CLEAN_USER_DATA = "django_python3_ldap.utils.clean_user_data"

# Path to a callable that takes a user model and a dict of {ldap_field_name: [value]},
# and saves any additional user relationships based on the LDAP data.
# Use this to customize how data loaded from LDAP is saved to User model relations.
# For customizing non-related User model fields, use LDAP_AUTH_CLEAN_USER_DATA.
LDAP_AUTH_SYNC_USER_RELATIONS = "django_python3_ldap.utils.sync_user_relations"

# Path to a callable that takes a dict of {ldap_field_name: value},
# returning a list of [ldap_search_filter]. The search filters will then be AND'd
# together when creating the final search filter.
LDAP_AUTH_FORMAT_SEARCH_FILTERS = "django_python3_ldap.utils.format_search_filters"

# Path to a callable that takes a dict of {model_field_name: value}, and returns
# a string of the username to bind to the LDAP server.
# Use this to support different types of LDAP server.
LDAP_AUTH_FORMAT_USERNAME = "django_python3_ldap.utils.format_username_openldap"

# Sets the login domain for Active Directory users.
LDAP_AUTH_ACTIVE_DIRECTORY_DOMAIN = None

# The LDAP username and password of a user for authenticating the `ldap_sync_users`
# management command. Set to None if you allow anonymous queries.
LDAP_AUTH_CONNECTION_USERNAME = None
LDAP_AUTH_CONNECTION_PASSWORD = None
