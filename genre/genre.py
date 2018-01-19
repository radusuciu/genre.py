from eyed3.utils.log import log as eyed3_log
import genre.config as config
import eyed3
import click
import discogs_client
import pathlib
import colorama
import pickle
import logging

# quiet about non-standard genres
eyed3_log.setLevel(logging.ERROR)

client = discogs_client.Client(config.USER_AGENT)
client.set_consumer_key(config.DISCOGS_KEY, config.DISCOGS_SECRET)

@click.command()
@click.option('--query', '-q',  help='Specify a query to use when searching for a matching track.')
@click.option('--yes-if-exact', '-y', help='Do not wait for user confirmtion if match is exact', flag_value=True)
@click.option('--dry-run', '-d', help='Perform lookup but do not write tags.', flag_value=True)
@click.argument('files', nargs=-1, type=click.Path(exists=True, dir_okay=False, readable=True, writable=True))
def main(files, query, yes_if_exact, dry_run):
    if auth():
        for file in files:
            process(file, query, yes_if_exact, dry_run)

def auth():
    auth_file_path = pathlib.Path(config.AUTH_FILE)

    if not auth_file_path.exists():
        token, secret, url = client.get_authorize_url()

        click.echo('Please browse to {}'.format(url))
        oauth_verifier = click.prompt('Please enter the code you received from discogs')

        try:
            token, secret = client.get_access_token(oauth_verifier)
            save_auth(auth_file_path, token, secret)
        except discogs_client.HTTPError:
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
    print(path, tag.artist, tag.album, query)
    if query:
        search_term = query
    elif tag and tag.artist and tag.album:
        search_term = '{} {}'.format(tag.artist, tag.album)
    else:
        search_term = path.stem

    return search_term

def process(file, query, yes_if_exact, dry_run):
    path = pathlib.Path(file).absolute()
    audio_file = eyed3.load(str(path))
    tag = audio_file.tag

    if not dry_run and not tag:
        audio_file.initTag(version=eyed3.id3.ID3_V2_3)
        tag = audio_file.tag

    search_term = get_search_term(path, tag, query)
    results = client.search(search_term, type='release')

    release = None

    if results.count and yes_if_exact:
        first_release = results[0]
        artist = ', '.join(artist.name for artist in first_release.artists)

        if search_term == '{} {}'.format(artist, first_release.title):
            release = first_release
            click.echo('Found exact match for {}: {}'.format(search_term, ', '.join(release.styles)))

    # if we have results, and haven't already found an exact match
    # then we iterate over results and ask user to enter the index 
    # of their choice
    if results.count and not release:
        click.echo('Choose option from below, 0 to skip, just press enter to pick first release.')

        for i, release in enumerate(results):
            artist = ', '.join(artist.name for artist in release.artists)
            click.echo('[{}]\t: {} - {} [{}]'.format(i + 1, artist, release.title, ', '.join(release.styles)))

        choice = click.prompt('Choice', type=int, default=1)
        # subtract by one to adjust for zero indexing
        release = results[choice - 1]
    elif not release:
        click.echo('No results found for {}'.format(search_term))

    tag.genre = ', '.join(release.styles)

    if release and not dry_run:
        tag.save(str(path))
    elif not release and dry_run:
        return False

    return True


if __name__ == '__main__':
    main()
