from eyed3.utils.log import log as eyed3_log
from discogs_client.exceptions import HTTPError
import genre.config as config
import eyed3
import click
import discogs_client
import pathlib
import colorama
import pickle
import logging
import time

# quiet about non-standard genres
eyed3_log.setLevel(logging.ERROR)

client = discogs_client.Client(config.USER_AGENT)
client.set_consumer_key(config.DISCOGS_KEY, config.DISCOGS_SECRET)

@click.command()
@click.option('--query', '-q',  help='Specify a query to use when searching for a matching track.')
@click.option('--yes-if-exact', '-y', help='Do not wait for user confirmtion if match is exact', flag_value=True)
@click.option('--skip-if-set', '-s', help='Skip lookup if a genre has already been set', flag_value=True)
@click.option('--dry-run', '-d', help='Perform lookup but do not write tags.', flag_value=True)
@click.argument('files', nargs=-1, type=click.Path(exists=True, dir_okay=False, readable=True, writable=True))
def main(files, query, yes_if_exact, skip_if_set, dry_run):
    if not auth():
        return False

    for file in files:
        retries = 0

        while retries < config.MAX_RETRIES:
            try:
                result = process(file, query, yes_if_exact, skip_if_set, dry_run)

                if result:
                    click.echo('Genre for:\t{} set to {}'.format(*result))
                else:
                    click.echo('Genre for:\t{} not changed'.format(file))
                break
            except HTTPError as e:
                if e.status_code == 429:
                    click.echo('Making too many requests to discogs, trying again in {} seconds.'.format(str(config.RETRY_PAUSE)))
                    retries = retries + 1
                    time.sleep(config.RETRY_PAUSE)
                    continue

        # pause for REQUEST_PAUSE seconds to avoid hammering discogs API too hard
        time.sleep(config.REQUEST_PAUSE)

def auth():
    auth_file_path = pathlib.Path(config.AUTH_FILE)

    if not auth_file_path.exists():
        token, secret, url = client.get_authorize_url()

        click.echo('Please browse to {}'.format(url))
        oauth_verifier = click.prompt('Please enter the code you received from discogs')

        try:
            token, secret = client.get_access_token(oauth_verifier)
            save_auth(auth_file_path, token, secret)
        except HTTPError:
            click.echo('Authetication failure.')
    else:
        client.set_token(*get_auth(auth_file_path))

    return True

def get_auth(auth_file_path):
    with auth_file_path.open('rb') as f:
        return pickle.load(f)

def save_auth(auth_file_path, token, secret):
    with auth_file_path.open('wb') as f:
        pickle.dump((token, secret), f)

def get_search_term(path, tag, query=None):
    # prefer to use existing tags and fall back to filename
    # unless a specific query is specified
    if query:
        search_term = query
    elif tag and tag.artist and tag.album:
        search_term = '{} {}'.format(tag.artist, tag.album)
    else:
        search_term = path.stem

    return search_term

def search_discogs(term):
    results = client.search(term, type='release')
    return results

def process(file, query, yes_if_exact, skip_if_set, dry_run):
    path = pathlib.Path(file).absolute()
    audio_file = eyed3.load(str(path))
    tag = audio_file.tag

    if not dry_run and not tag:
        audio_file.initTag(version=eyed3.id3.ID3_V2_3)
        tag = audio_file.tag

    search_term = get_search_term(path, tag, query)
    click.echo('Processing {}'.format(path.name))
    click.echo('Search term: {}'.format(search_term))
    click.echo('Processing:\t{}'.format(path.name))
    click.echo('Search term:\t{}'.format(search_term))

    if skip_if_set and tag.genre:
        click.echo('Skipping:\t{}, genre is already set to {}'.format(path.name, tag.genre))
        return False

    results = search_discogs(search_term)
    release = None

    if results.count and yes_if_exact:
        first_release = results[0]
        artist = ', '.join(artist.name for artist in first_release.artists)

        if search_term == '{} {}'.format(artist, first_release.title):
            release = first_release
            styles = release.styles if release.styles else release.genres
            click.echo('Found exact match for {}: {}'.format(search_term, ', '.join(styles)))

    # if we have results, and haven't already found an exact match
    # then we iterate over results and ask user to enter the index 
    # of their choice
    if results.count and not release:
        click.echo('Choose option from below, 0 to skip, just press enter to pick first release.')

        for i, rel in enumerate(results):
            if i == config.MAX_SEARCH_RESULTS:
                break
            artist = ', '.join(artist.name for artist in rel.artists)
            styles = rel.styles if rel.styles else rel.genres
            click.echo('[{}]\t: {} - {} [{}]'.format(i + 1, artist, rel.title, ', '.join(styles)))

        choice = click.prompt('Choice', type=int, default=1)
        # subtract by one to adjust for zero indexing
        if choice:
            release = results[choice - 1]
        elif choice <= 0:
            click.echo('Skipping:\t{}'.format(path.name))
    elif not results.count:
        click.echo('No results found for {}'.format(search_term))

    if release:
        genre = ', '.join(release.styles)
        tag.genre = genre
        if not dry_run:
            tag.save(str(path))
        return (path.name, genre)

    return False



if __name__ == '__main__':
    main()
