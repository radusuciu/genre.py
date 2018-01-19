"""Setup script for genre.py."""
from setuptools import setup, find_packages, Command
from shutil import rmtree
import codecs
import io
import os
import sys

here = os.path.abspath(os.path.dirname(__file__))

# we need api secrets to be distributed with package
secrets_path = os.path.join(here, 'genre/secrets.yml')
actual_secrets_path = os.path.join(here, 'genre/secrets.override.yml')
if not os.path.exists(actual_secrets_path):
    print('Error: secrets.override.yml is required')
    sys.exit()


def read(*parts):
    """Return multiple read calls to different readable objects as a single
    string."""
    return codecs.open(os.path.join(here, *parts), 'r').read()

def read_md(file):
    try:
        from pypandoc import convert
        return convert(file, 'rst')
    except ImportError:
        print('Error: pypandoc module not found, could not convert Markdown to RST')


NAME = 'genre.py'
DESCRIPTION = 'genre.py looks up the genre of a particular album on discogs and updates ID3 data accordingly.'
LONG_DESCRIPTION = read_md('README.md')
URL = 'http://github.com/radusuciu/genre.py'
EMAIL = 'radusuciu@gmail.com'
AUTHOR = 'Radu Suciu'

REQUIRED = read('requirements.txt').splitlines()

# not doing import because do not want to have to load module
# before it has been installed
version_path = os.path.join(here, 'genre/version.py')
exec(read(version_path))
VERSION = __version__


# from github.com/kennethreitz/setup.py
class UploadCommand(Command):
    """Support setup.py upload."""

    description = 'Build and publish the package.'
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        self.status('Building Source and Wheel (universal) distribution…')
        os.system('{0} setup.py sdist bdist_wheel --universal'.format(sys.executable))

        self.status('Uploading the package to PyPi via Twine…')
        os.system('twine upload dist/*')

        sys.exit()


setup(
    name=NAME,
    version=VERSION,
    url=URL,
    author=AUTHOR,
    author_email=EMAIL,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    install_requires=REQUIRED,
    packages=find_packages(exclude=('tests',)),
    entry_points={
        'console_scripts': ['genre-py=genre:main']
    },
    include_package_data=True,
    platforms='any',
    zip_safe=True,
    license='Apache Software License',
    classifiers=[
        'Environment :: Console',
        'Topic :: Multimedia :: Sound/Audio :: Editors',
        'Intended Audience :: End Users/Desktop',
        'Programming Language :: Python :: 3',
        'Development Status :: 3 - Alpha',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    # $ setup.py publish support.
    cmdclass={
        'upload': UploadCommand,
    },
)
