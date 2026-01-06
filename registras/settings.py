"""
Django settings for registras project.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security ---
SECRET_KEY = 'django-insecure-x30nv(zk%f6zbytg#%bi$=nq@81c3t#04d!r10ldr5g1^h&t$='
DEBUG = True
ALLOWED_HOSTS = []

# --- Applications ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'simple_history',

    # third-party
    'django_extensions',

    # local
    'pozicijos.apps.PozicijosConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'registras.urls'

# --- Templates ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'registras.wsgi.application'

# --- Database ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Localization ---
LANGUAGE_CODE = 'lt'
TIME_ZONE = 'Europe/Vilnius'
USE_I18N = True
USE_TZ = True

DATE_FORMAT = 'Y-m-d'
DATE_INPUT_FORMATS = ['%Y-%m-%d']

# --- Static & Media ---
STATIC_URL = '/static/'

# Projektinis static katalogas (pasirinktinai).
# Jei katalogo nėra – jo neįtraukiam, kad nebūtų W004 warning.
STATICFILES_DIRS = []
PROJECT_STATIC_DIR = BASE_DIR / "static"
if PROJECT_STATIC_DIR.exists():
    STATICFILES_DIRS.append(PROJECT_STATIC_DIR)

# Collectstatic output (NEdėti į STATICFILES_DIRS, kitaip bus E002)
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- Default primary key field ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===================== Pasiūlymo (offer) nustatymai =====================
OFFER_COMPANY_NAME = "ELAMETA UAB"
OFFER_COMPANY_LINE1 = "J. Basanavičiaus g. 114N, LT-28214, Utena"
OFFER_COMPANY_LINE2 = "Tel. +370 000 00000, el. paštas info@elameta.lt"
