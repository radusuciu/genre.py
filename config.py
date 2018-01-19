import pathlib
import yaml
import os

PROJECT_HOME_PATH = pathlib.Path(os.path.realpath(__file__)).parent
_secrets_path = PROJECT_HOME_PATH.joinpath('secrets.yml')
_override_path = PROJECT_HOME_PATH.joinpath('secrets.override.yml')

# get secrets
with _secrets_path.open() as f:
    _SECRETS = yaml.load(f)

# override secrets if possible
# this override file should not be checked into version control!
if _override_path.is_file():
    with _override_path.open() as f:
        _SECRETS.update(yaml.load(f))


DISCOGS_KEY = _SECRETS['discogs']['KEY']
DISCOGS_SECRET = _SECRETS['discogs']['SECRET']

USER_AGENT = 'genre.py'
AUTH_FILE = 'discogs.auth'