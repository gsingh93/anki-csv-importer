#!/usr/bin/env python3

import argparse
import anki
from anki.importing import TextImporter
import requests
import os
import tempfile


def download_csv(sheet_url):
    print('[+] Downloading CSV')
    r = requests.get(sheet_url)

    path = None
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(r.content)
        path = f.name

    print('[+] Wrote CSV to {}'.format(f.name))
    return f.name


def import_csv(col, csv_path, deck_name, note_type, local_file, allow_html):
    print('[+] Importing CSV from {}'.format(csv_path))

    # Select the deck, creating it if it doesn't exist
    did = col.decks.id(deck_name)
    col.decks.select(did)

    # Anki defaults to the last note type used in the selected deck
    model = col.models.byName(note_type)
    deck = col.decks.get(did)
    deck['mid'] = model['id']
    col.decks.save(deck)

    # Anki puts cards in the last deck used by the note type
    model['did'] = did

    # Import the CSV into the collection
    ti = TextImporter(col, csv_path)
    ti.allowHTML = allow_html
    ti.initMapping()
    ti.run()

    # If we downloaded this file from a URL, clean it up
    if not local_file:
        os.remove(csv_path)
        print('[+] Removed temporary files')

    # Required when running scripts outside of Anki to close the DB connection
    # and save the changes. Sets cwd back to what it was before.
    col.close()

    print('[+] Finished importing CSV')


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Import a local or remote CSV file into Anki')

    parser.add_argument(
        '-p',
        '--path',
        help='the path of the local CSV file')
    parser.add_argument(
        '-u',
        '--url',
        help='the URL of the remote CSV file')

    parser.add_argument(
        '-d',
        '--deck',
        help='the name of the deck to import the sheet to',
        required=True)
    parser.add_argument(
        '-n',
        '--note',
        help='the card type to import',
        required=True)
    parser.add_argument(
        '-c',
        '--col',
        help='the path to the .anki2 collection',
        required=True)

    parser.add_argument(
        '--allow-html',
        help='render HTML instead of treating it as plaintext',
        action="store_true")

    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.path and args.url:
        print('[E] Only one of --path and --url can be supplied')
        exit(1)

    if not (args.path or args.url):
        print('[E] You must specify either --path or --url')
        exit(1)

    # Store the cwd because it's about to change
    cwd = os.getcwd()

    # Normally you use aqt.mw.col to access the collection, but we don't want
    # to use the GUI. Note that this changes the cwd to the Anki
    # collection.media directory
    col = anki.Collection(args.col)

    local_file = None
    if args.url:
        # Download the CSV to a tempfile
        csv_path = download_csv(args.url)
        local_file = False
    elif args.path:
        # Use an existing CSV file
        csv_path = os.path.join(cwd, args.path)
        local_file = True
    else:
        assert False  # Should never reach here

    assert local_file is not None
    import_csv(
        col,
        csv_path,
        args.deck,
        args.note,
        local_file,
        args.allow_html)


main()
