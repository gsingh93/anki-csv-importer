#!/usr/bin/env python3

import argparse
import csv
import requests
import os
import tempfile

ANKI_CONNECT_URL = 'http://localhost:8765'


def parse_ac_response(response):
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']


def make_ac_request(action, **params):
    return {'action': action, 'params': params, 'version': 6}


def invoke_ac(action, **params):
    requestJson = make_ac_request(action, **params)
    try:
        response = requests.post(ANKI_CONNECT_URL, json=requestJson).json()
    except requests.exceptions.ConnectionError:
        print('[E] Failed to connect to AnkiConnect, make sure Anki is running')
        exit(1)

    return parse_ac_response(response)


def invoke_multi_ac(multi_actions):
    multi_results = invoke_ac('multi', actions=multi_actions)
    results = []
    for res in multi_results:
        results.append(parse_ac_response(res))
    return results


def csv_to_ac_notes(csv_path, deck_name, note_type):
    notes = []
    index_to_field_name = {}
    with open(csv_path) as csvfile:
        reader = csv.reader(csvfile)
        for i, row in enumerate(reader):
            fields = {}
            tags = None
            if i == 0:
                for j, field_name in enumerate(row):
                    index_to_field_name[j] = field_name
            else:
                for j, field_value in enumerate(row):
                    field_name = index_to_field_name[j]
                    if field_name.lower() == 'tags':
                        tags = field_value.split(' ')
                    else:
                        fields[field_name] = field_value

                note = {
                    'deckName': deck_name,
                    'modelName': note_type,
                    'fields': fields,
                    'tags': tags,
                    'options': {
                        "allowDuplicate": False,
                        "duplicateScope": "deck"
                    }
                }
                notes.append(note)

    return notes


def get_ac_add_and_update_note_lists(notes):
    result = invoke_ac('canAddNotes', notes=notes)

    notes_to_add = []
    notes_to_update = []
    for i, b in enumerate(result):
        if b:
            notes_to_add.append(notes[i])
        else:
            notes_to_update.append(notes[i])

    return notes_to_add, notes_to_update


def ac_update_notes_and_get_note_info(notes_to_update, find_note_results):
    actions = []
    for i, n in enumerate(notes_to_update):
        front = n['fields']['Front']

        find_note_result = find_note_results[i]
        if len(find_note_result) == 0:
            print('[W] Did not find any results for note with front "{}", '
                  'skipping. This is likely a bug, '
                  'please report this to the developer'.format(front))
            continue
        elif len(find_note_result) > 1:
            print('[W] Duplicate notes are not supported, '
                  'skipping note with front "{}"'.format(front))
            continue

        # The updateNoteFields parameter is the same as the addNote parameter
        # but with an additional ID field
        n['id'] = find_note_result[0]
        actions.append(make_ac_request('updateNoteFields', note=n))

        actions.append(make_ac_request('notesInfo', notes=[n['id']]))
        actions.append(
            make_ac_request(
                'addTags',
                notes=[n['id']],
                tags=' '.join(n['tags'])))

    # Only the results for note info are not None
    note_info_results = [res for res in invoke_multi_ac(actions) if res is not None]

    # We need the note info result for a note to be at the same index in
    # note_info_results as the index of the note in notes_to_update. However,
    # because we may skip notes that are not found or are duplicates, there may
    # not be a result for a note and thus the indices may not match. Removing
    # all notes where we did not set an 'id' field should cause the IDs to match
    # up again.
    new_notes_to_update = [n for n in notes_to_update if 'id' in n]

    assert len(note_info_results) == len(new_notes_to_update)
    return new_notes_to_update, note_info_results


def ac_remove_tags(notes_to_update, note_info_results):
    remove_tags_actions = []
    for i, n in enumerate(notes_to_update):
        note_info_result = note_info_results[i]
        assert(len(note_info_result) == 1)

        existing_tags = note_info_result[0]['tags']
        tags_to_remove = list(set(existing_tags) - set(n['tags']))

        remove_tags_actions.append(
            make_ac_request(
                'removeTags',
                notes=[n['id']],
                tags=' '.join(tags_to_remove)))

    invoke_multi_ac(remove_tags_actions)


def send_to_anki_connect(
        csv_path,
        deck_name,
        note_type):
    # TODO: Audio, images
    notes = csv_to_ac_notes(csv_path, deck_name, note_type)

    # Create the deck, if it already exists this will not overwrite it
    invoke_ac('createDeck', deck=deck_name)

    # See which notes can be added
    notes_to_add, notes_to_update = get_ac_add_and_update_note_lists(notes)

    print('[+] Adding {} new notes and updating {} existing notes'.format(
        len(notes_to_add),
        len(notes_to_update)))
    invoke_ac('addNotes', notes=notes_to_add)

    # Find the IDs of the existing notes
    find_note_actions = []
    for n in notes_to_update:
        front = n['fields']['Front'].replace('"', '\\"')
        query = 'deck:"{}" "front:{}"'.format(n['deckName'], front)
        find_note_actions.append(make_ac_request('findNotes', query=query))
    find_note_results = invoke_multi_ac(find_note_actions)

    # Update notes and get the note info so we can remove old tags
    new_notes_to_update, note_info_results = ac_update_notes_and_get_note_info(
        notes_to_update, find_note_results)

    print('[+] Removing deleted tags from notes')
    ac_remove_tags(new_notes_to_update, note_info_results)


def download_csv(sheet_url):
    print('[+] Downloading CSV')
    r = requests.get(sheet_url)

    path = None
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(r.content)
        path = f.name

    print('[+] Wrote CSV to {}'.format(f.name))
    return f.name


def import_csv(col, csv_path, deck_name, note_type, allow_html, skip_header):
    import anki
    from anki.importing import TextImporter

    print('[+] Importing CSV from {}'.format(csv_path))

    if skip_header:
        # Remove the first line from the CSV file if the skip_header argument
        # was provided
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp:
            with open(csv_path, 'r') as f:
                tmp.writelines(f.read().splitlines()[1:])
                csv_path = tmp.name
        print('[+] Removed CSV header and wrote new file to {}'.format(csv_path))

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
    ti = anki.importing.TextImporter(col, csv_path)
    ti.allowHTML = allow_html
    ti.initMapping()
    ti.run()

    # Required when running scripts outside of Anki to close the DB connection
    # and save the changes. Sets cwd back to what it was before.
    col.close()

    if skip_header:
        # Cleanup temporary file. The original file gets cleaned up in main if
        # necessary
        os.remove(csv_path)

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
        help='the note type to import',
        required=True)

    parser.add_argument(
        '--no-anki-connect',
        help='write notes directly to Anki DB without using AnkiConnect',
        action='store_true')
    parser.add_argument(
        '-c',
        '--col',
        help='the path to the .anki2 collection (only when using --no-anki-connect)')
    parser.add_argument(
        '--allow-html',
        help='render HTML instead of treating it as plaintext (only when using --no-anki-connect)',
        action='store_true')
    parser.add_argument(
        '--skip-header',
        help='skip first row of CSV (only when using --no-anki-connect)',
        action='store_true')

    return parser.parse_args()


def validate_args(args):
    if args.path and args.url:
        print('[E] Only one of --path and --url can be supplied')
        exit(1)

    if not (args.path or args.url):
        print('[E] You must specify either --path or --url')
        exit(1)

    if args.no_anki_connect:
        if not args.col:
            print('[E] --col is required when using --no-anki-connect')
            exit(1)
    else:
        if args.skip_header:
            print('[E] --skip-header is only supported with --no-anki-connect')
            exit(1)
        elif args.allow_html:
            print('[E] --allow-html is only supported with --no-anki-connect, '
                  'when using AnkiConnect HTML is always enabled')
            exit(1)
        elif args.col:
            print('[E] --col is only supported with --no-anki-connect')
            exit(1)


def main():
    args = parse_arguments()
    validate_args(args)

    if args.url:
        # Download the CSV to a tempfile
        csv_path = download_csv(args.url)
    elif args.path:
        # Use an existing CSV file. We convert this to an absolute path because
        # CWD might change later
        csv_path = os.path.abspath(args.path)
    else:
        assert False  # Should never reach here

    if args.no_anki_connect:
        import anki

        # Normally you use aqt.mw.col to access the collection, but we don't want
        # to use the GUI. Note that this changes the cwd to the Anki
        # collection.media directory
        col = anki.Collection(args.col)

        import_csv(
            col,
            csv_path,
            args.deck,
            args.note,
            args.allow_html,
            args.skip_header)
        print('[W] Cards cannot be automatically synced, '
              'open Anki to sync them manually')
    else:
        send_to_anki_connect(
            csv_path,
            args.deck,
            args.note)
        print('[+] Syncing')
        invoke_ac("sync")

    # If we downloaded this file from a URL, clean it up
    if args.url:
        os.remove(csv_path)
        print('[+] Removed temporary files')


main()
