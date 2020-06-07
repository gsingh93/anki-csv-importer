# Anki CSV Importer

Imports a local CSV file or a remote CSV file at a URL (including files stored in Google Sheets) into an Anki deck

## Table of Contents

* [Usage](#usage)
* [Instructions](#instructions)
   * [Using AnkiConnect (Recommended)](#using-ankiconnect-recommended)
   * [Without AnkiConnect](#without-ankiconnect)
      * [collection_path](#collection_path)
* [Getting the CSV URL for a Google Sheet](#getting-the-csv-url-for-a-google-sheet)
* [CSV format](#csv-format)
   * [When using AnkiConnect](#when-using-ankiconnect)
   * [When using --no-anki-connect](#when-using---no-anki-connect)
* [HTML Formatting](#html-formatting)
* [How sheet modifications are handled](#how-sheet-modifications-are-handled)
* [Notes](#notes)
* [TODO](#todo)
* [License](#license)

## Usage

```
usage: anki-csv-importer.py [-h] [-p PATH] [-u URL] -d DECK -n NOTE
                            [--no-anki-connect] [-c COL] [--allow-html]
                            [--skip-header]

Import a local or remote CSV file into Anki

optional arguments:
  -h, --help            show this help message and exit
  -p PATH, --path PATH  the path of the local CSV file
  -u URL, --url URL     the URL of the remote CSV file
  -d DECK, --deck DECK  the name of the deck to import the sheet to
  -n NOTE, --note NOTE  the note type to import
  --no-anki-connect     write notes directly to Anki DB without using
                        AnkiConnect
  -c COL, --col COL     the path to the .anki2 collection (only when using
                        --no-anki-connect)
  --allow-html          render HTML instead of treating it as plaintext (only
                        when using --no-anki-connect)
  --skip-header         skip first row of CSV (only when using --no-anki-
                        connect)
```

## Instructions

### Using AnkiConnect (Recommended)

1. The recommended way to use this script is with the [AnkiConnect plugin](https://ankiweb.net/shared/info/2055492159). Install this like you would any other Anki plugin.
1. Install Python3 and `pip3`
1. Clone this repository (`git clone https://github.com/gsingh93/anki-csv-importer`) or download and unzip the source code from [here](https://github.com/gsingh93/anki-csv-importer/archive/master.zip)
1. Open a terminal in the source code directory and run `pip3 install requests`
1. Make sure Anki **is running** and run one of the commands below. The double quotes in the command are required if the parameters contain any spaces or special characters. If the specified deck does not exist, it will be created
    1. For a local CSV file run `./anki-csv-importer.py --path "<path>" --deck "<deck_name>" --note "<note_type>"`
    1. For a remote CSV file run `./anki-csv-importer.py --url "<url>" --deck "<deck_name>" --note "<note_type>"`. See [this section](#getting-the-csv-url-for-a-google-sheet) to get the CSV URL for a Google Sheet

A sync is automatically run after the notes are added. See the [Notes](#Notes) section for how to continuously sync the CSV to Anki while hiding the Anki window.

### Without AnkiConnect

The original vision for this script was to have cards synced from a CSV (ideally a Google Sheet) to Anki without ever having to open the Anki desktop application (but still accessible on other platforms like AnkiDroid). However, there are two issues with this approach:
1. Anki does not support syncing through the Python API. Only actual plugins can do this. This means that while notes can be added to the desktop version of Anki, they cannot be synced to the Anki server and thus they will not be accessible on other platforms like Android until Anki is opened and a sync occurs.
2. The version of the `anki` Python package on PyPi may not necessarily correspond to the version of Anki you have installed. If there is a mismatch between the two versions, then each may have a different database schema, and so **using this script may lead to data corruption**. Use at your own risk. If you would like to go this route, create a backup for your collection file before testing this, and try to use the latest version of Anki, which may be different from the stable version of Anki. Once you see that the script is successfully able to import notes, there should be no risk of data corruption unless you update the desktop application or the Python library.

If you are fine with the above two issues, follow these instructions:

1. Install Python 3 and `pip3`
1. Clone this repository (`git clone https://github.com/gsingh93/anki-csv-importer`) or download and unzip the source code from [here](https://github.com/gsingh93/anki-csv-importer/archive/master.zip)
1. Open a terminal in the source code directory and run `pip3 install -r requirements.txt`
1. Make sure Anki **is not running** and run one of the commands below. The double quotes in the command are required if the parameters contain any spaces or special characters. If the specified deck does not exist, it will be created
    1. For a local CSV file run `./anki-csv-importer.py --path "<path>" --deck "<deck_name>" --note "<note_type>" --col "<collection_path>"` --no-anki-connect
    1. For a remote CSV file run `./anki-csv-importer.py --url "<url>" --deck "<deck_name>" --note "<note_type>" --col "<collection_path>" --no-anki-connect`. See [this section](#getting-the-csv-url-for-a-google-sheet) to get the CSV URL for a Google Sheet
1. Open Anki, view the deck to confirm the import was successful, and trigger a sync

#### `collection_path`

To find the value for `collection_path`, see [the Anki documentation](https://docs.ankiweb.net/#/files?id=file-locations) to see where the Anki folder for your system is:

> On Windows, the latest Anki versions store your Anki files in your appdata folder. You can access it by opening the file manager, and typing %APPDATA%\Anki2 in the location field. Older versions of Anki stored your Anki files in a folder called Anki in your Documents folder.
>
> On Mac computers, recent Anki versions store all their files in the ~/Library/Application Support/Anki2 folder. The Library folder is hidden by default, but can be revealed in Finder by holding down the option key while clicking on the Go menu. If you’re on an older Anki version, your Anki files will be in your Documents/Anki folder.
>
> On Linux, recent Anki versions store your data in ~/.local/share/Anki2, or $XDG_DATA_HOME/Anki2 if you have set a custom data path. Older versions of Anki stored your files in ~/Documents/Anki or ~/Anki.

Then add `<profile_name>/collection.anki2` to that path. For example, if your profile is named `Foo` and you are on MacOS, the `collection_path` would be `~/Library/Application Support/Anki2/Foo/collection.anki2`

## Getting the CSV URL for a Google Sheet

1. Create a new Google Sheet or open an existing Sheet
2. Click the "Share" button, followed by "Get shareable link", and then "Anyone with the link can view"
3. Open the developer tools in your browser and open the "Network" tab
4. In Google Sheets click "File -> Download -> Comma-separated values (.csv, current sheet)"
5. Right click on the network request in the developer tools and click "Copy -> Copy link address" (for Chrome, instructions may vary for other browsers)

## CSV format

### When using AnkiConnect

The first row of the CSV must contain the names of the fields of the note type, and it may optionally contain 'Tags' to specify which column should be used for tags.

For example, if the note has the three fields `question`, `answer`, `some_field`, then the CSV file should look something like
```
Question,Answer,Some Field,Tags
question1,answer1,some_field1,tags1
question2,answer2,some_field1,tags1
...
```

### When using --no-anki-connect

Each column of the CSV corresponds to a field in a note. No header row is needed, the first row can be the data for the first note. After all the columns for the note fields, the next column is for tags. If you would like a header row in your CSV but want to avoid having it imported as a note, use the `--skip-header` flag.

For example, if the note has the three fields `question`, `answer`, `some_field`, then the CSV file should look something like
```
question1,answer1,some_field1,tags1
question2,answer2,some_field1,tags1
...
```

If the CSV contains more columns than the number of fields in the specified note plus one (for the tags field), they will be ignored. If there are less columns in the CSV than in the note, they will be blank in the note.

## HTML Formatting

HTML formatting is enabled when using AnkiConnect and currently cannot be disabled.

When using `--no-anki-connect`, HTML formatting is disabled by default; any HTML tags are not rendered and displayed as plaintext. If you would like to render it, you can use the `--allow-html` flag. For example, to add a link to `https://google.com` in a field, use `<a href="https://google.com">https://google.com</a>`. When using `--allow-html`, you must make sure your HTML formatting is correct or notes can be incorrectly imported into Anki.

To display HTML as plaintext when HTML formatting is enabled is enabled, you can use [HTML escape entities](https://www.w3schools.com/html/html_entities.asp). For example, to display `<b>` as plaintext, you would enter `&lt;b&gt;`.

## How sheet modifications are handled

This is the default behavior of Anki's `TextImporter`:

- When a new row is added or the "primary field" (i.e. "Front") is changed in the Google Sheet, a new note is added to the Anki deck
- When any column other than the "primary field" is updated in the Google Sheet, the note in the deck is updated with the new fields. Review time does not change.
- When a row is deleted, it's not deleted from the Anki deck

## Notes

- This script should theoretically work on MacOS, Windows, and Linux, but it has only been tested on MacOS
- Adding media to notes is not supported at the moment
- If you would like to keep your Anki deck continuously in sync with a remote CSV file, setup a cron job on MacOS and Linux or a scheduled task on Windows to run the command at some regular interval.
  - When using AnkiConnect, this requires you to keep Anki constantly open, or launch it in your cron job. There are various solutions on different platforms to do this while hiding the window. For example, on MacOS you can use [this solution](https://apple.stackexchange.com/a/349641) combined with minimizing the window or moving it to an unused desktop, and for Windows you can use applications like [RBTray](http://rbtray.sourceforge.net/).
- Use the [Add row to Google Sheets](https://chrome.google.com/webstore/detail/add-row-to-google-sheets/baikkcmfolbapkeefcdccadmelcnijcd) extension to add questions to a Google Sheet while you browse the web, and then use this script to keep that Sheet in sync with Anki

## TODO

- Support audio and images when using AnkiConnect

## License

[MIT](./LICENSE)
