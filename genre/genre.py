from eyed3.utils.log import log as eyed3_log
from discogs_client.exceptions import HTTPError
import genre.config as config
from eyed3.id3 import Genre
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
@click.option('--query', '-q',  help='Specify a query to use when searching for a matching track')
@click.option('--max-genres', '-m',  help='Maximum number of genres to allow in a tag', default=config.DEFAULT_MAX_GENRES)
@click.option('--yes-if-exact', '-y', help='Do not wait for user confirmation if match is exact', flag_value=True)
@click.option('--skip-if-set', '-s', help='Skip lookup if a genre has already been set', flag_value=True)
@click.option('--reset-genre', '-r', help='Reset genre before looking up', flag_value=True)
@click.option('--dry-run', '-d', help='Perform lookup but do not write tags.', flag_value=True)
@click.version_option(version=config.VERSION)
@click.argument('files', nargs=-1, type=click.Path(exists=True, dir_okay=False, readable=True, writable=True))
def main(files, query, max_genres, yes_if_exact, skip_if_set, reset_genre, dry_run):
    if not auth():
        return False

    for file in files:
        retries = 0

        while retries < config.MAX_RETRIES:
            try:
                result = process(file, query, max_genres, yes_if_exact, skip_if_set, reset_genre, dry_run)

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

def search_discogs(path, tag, query):
    # prefer to use existing tags and fall back to filename
    # unless a specific query is specified
    use_tag =  tag and tag.artist and tag.album

    if query or not use_tag:
        results = client.search(query if query else path.stem, type='release')
    elif use_tag:
        results = client.search(tag.album, artist=tag.artist, album=tag.album, type='release')

    return results


def is_exact_match(tag, release):
    # report exact match only for files with tags
    if not (tag and tag.artist and tag.album):
        return False

    release_artists = set(artist.name for artist in release.artists)
    tag_artists = set(a.strip() for a in tag.artist.split(','))

    return release_artists == tag_artists and release.title == tag.album


def process(file, query, max_genres, yes_if_exact, skip_if_set, reset_genre, dry_run):
    path = pathlib.Path(file).absolute()
    audio_file = eyed3.load(str(path))
    tag = audio_file.tag

    if not dry_run and not tag:
        audio_file.initTag(version=eyed3.id3.ID3_V2_3)
        tag = audio_file.tag

    click.echo('Processing:\t{}'.format(path.name))
    click.echo('Artist: {}, Title: {}, Album: {}, Genre: {}'.format(
        tag.artist, tag.title, tag.album, tag.genre
    ))

    if reset_genre:
        tag.genre = Genre()
        if not dry_run:
            tag.save()

    if skip_if_set and tag.genre:
        click.echo('Skipping:\t{}, genre is already set to {}'.format(path.name, tag.genre))
        return False

    results = search_discogs(path, tag, query)
    release = None

    if results.count and yes_if_exact and is_exact_match(tag, results[0]):
        release = results[0]
        styles = release.styles[:max_genres] if release.styles else release.genres
        click.echo('Found exact match for {}: {}'.format(path.name, ', '.join(styles)))

    # if we have results, and haven't already found an exact match
    # then we iterate over results and ask user to enter the index 
    # of their choice
    if results.count and not release:
        click.echo('Choose option from below, 0 to skip, just press enter to pick first release.')

        for i, rel in enumerate(results):
            if i == config.MAX_SEARCH_RESULTS:
                break
            artist = ', '.join(artist.name for artist in rel.artists)
            styles = rel.styles[:max_genres] if rel.styles else rel.genres
            click.echo('[{}]\t: {} - {} [{}]'.format(i + 1, artist, rel.title, ', '.join(styles)))

        choice = click.prompt('Choice', type=int, default=1)
        # subtract by one to adjust for zero indexing
        if choice:
            release = results[choice - 1]
        elif choice <= 0:
            click.echo('Skipping:\t{}'.format(path.name))
    elif not results.count:
        click.echo('No results found for {}'.format(path.stem))

    if release:
        genre = ', '.join(release.styles[:max_genres])
        tag.genre = genre
        if not dry_run:
            tag.save(str(path))
        return (path.name, genre)

    return False



if __name__ == '__main__':
    main()
