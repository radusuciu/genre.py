from pkg_resources import resource_string
from version import __version__
import pathlib
import yaml
import os

PROJECT_HOME_PATH = pathlib.Path(os.path.realpath(__file__)).parent
VERSION = __version__

try:
    _secrets_path = PROJECT_HOME_PATH.joinpath('secrets.yml')
    _override_path = PROJECT_HOME_PATH.joinpath('secrets.override.yml')
    # get secrets
    _SECRETS = yaml.load(_secrets_path.read_text())

    # override secrets if possible
    # this override file should not be checked into version control!
    if _override_path.is_file():
        _SECRETS.update(yaml.load(_override_path.read_text()))
except NotADirectoryError:
    _SECRETS = yaml.load(resource_string('genre', 'secrets.yml'))
    _SECRETS.update(yaml.load(resource_string('genre', 'secrets.override.yml')))

DISCOGS_KEY = _SECRETS['discogs']['KEY']
DISCOGS_SECRET = _SECRETS['discogs']['SECRET']

USER_AGENT = 'genre.py'
AUTH_FILE = 'discogs.auth'

# max search results per query to discogs
MAX_SEARCH_RESULTS = 5

# max number of retries
MAX_RETRIES = 2 

# time in seconds to wait between requests
REQUEST_PAUSE = 1

# time in seconds to wait between retries
RETRY_PAUSE = 30

# default max number of genres to allow in a tag, can be overwritten by tag
DEFAULT_MAX_GENRES = 3
