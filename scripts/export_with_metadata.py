"""Add metadata to a PDF file attached to a Zotero item.

This script clones an existing PDF file, setting the "/Author" and
"/Title" metadata fields according to values stored in the Zotero database.

The PDF to be cloned must be attached to a Zotero parent item. This
script then queries the Zotero database to retrieve the title and
author(s) of this parent item.

It should be noted that this script *does not* use the web API to
Zotero; rather, it uses SQLite queries to the *local* Zotero
database. Therefore, the user is encouraged to sync with zotero.org
prior to running this script. Also, the Zotero desktop client should be
closed while this script runs. Failing to do so will trigger the
following error message

    sqlite3.OperationalError: database is locked

The script first tries to find the user's Zotero profile (a file that is
called prefs.js). In case of failure, it is possible to specify the
relevent preferences from the command line (see the --data and --base
options).
"""
import os.path
import sqlite3
import sys

import PyPDF2

import pyzottk

from argparse import ArgumentParser, RawDescriptionHelpFormatter

PATH_HELP = ('The path to the attachment file. Both linked and stored '
             'attachments are allowed. Path to the former must start '
             'with "attachments:", while path to the latter must be a '
             'true file path. The specified path is passed to a SQLite '
             'LIKE clause. As such, wildcards "_" (single character) '
             'and "%%" (multiple characters) are accepted.')
OUTPUT_HELP = ('The path to the cloned PDF (with metadata). If not '
               'provided, the cloned PDF file will be stored in the '
               'current directory, under the name '
               '"input-with_metadata.pdf", where "input.pdf" is the '
               'name of the input file.')
DATA_HELP = ('Full path to the Zotero database. When this option is '
             'set, the Zotero preferences files prefs.js is not '
             'loaded.')
BASE_HELP = ('The path to the root directory of linked attachments. '
             'This corresponds to the baseAttachmentPath key in the '
             'prefs.js Zotero preferences files. This option is ignored '
             'if --data is not specified. It is required to export '
             'linked attachments when the --data option is specified.')

ATTACHMENTS_PREFIX = 'attachments:'
PDF_EXTENSION = '.pdf'
WITH_METADATA = '-with_metadata'

# Preference keys (to be found in the prefs.js file)
BASE_ATTACHMENT_PATH_KEY = 'extensions.zotero.baseAttachmentPath'
DATA_DIR_KEY = 'extensions.zotero.dataDir'


def get_field_ID(field_name, cursor):
    """Return the ID for the specified name in the Zotero table fields.

    Args:
        field_name: The value of the column fieldName.
        cursor: The Cursor object through which the SQLite queries are
            sent to the Zotero database.

    Returns:
        The value of the column fieldID that matches field_name in the
        Zotero table fields.
    """
    query = 'SELECT fieldID FROM fields WHERE fields.fieldName=?'
    cursor.execute(query, (field_name,))
    field_ID, = cursor.fetchone()
    return field_ID


def get_title(item_ID, cursor, field_ID=None):
    """Return the title of the item in the Zotero database.

    Args:
        item_ID: The value of the column itemID in the Zotero table
            itemData
        cursor: The Cursor object through which the SQLite queries are
            sent to the Zotero database.
        field_ID: In the fields table, the fieldID column value of the
            entry whose fieldValue column value is: title. If None, the
            function first queries for it.

    Returns:
        The title of the item.
    """
    if field_ID is None:
        field_ID = get_field_ID('title', cursor)

    query = ('SELECT itemDataValues.value '
             'FROM itemData INNER JOIN itemDataValues '
             'ON itemData.valueID=itemDataValues.valueID '
             'WHERE itemData.itemID=? AND itemData.fieldID=?')
    cursor.execute(query, (item_ID, field_ID))
    title, = cursor.fetchone()

    return title


def get_authors(itemID, cursor):
    """Return the authors of the item in the Zotero database.

    The authors are returned as a single string of coma separated last
    names.

    """
    query = ('SELECT itemCreators.orderIndex, creators.lastName '
             'FROM itemCreators INNER JOIN creators '
             'ON itemCreators.creatorID=creators.creatorID '
             'WHERE itemCreators.itemID=?')
    cursor.execute(query, (itemID,))
    authors = [lastName for _, lastName in sorted(cursor, key=lambda t: t[0])]

    if len(authors) == 1:
        return authors[0]
    else:
        return ', '.join(authors[:-1])+' and '+authors[-1]


def find_attachments(pattern, cursor):
    """Return a list of attachments that match the specified pattern.

    Args:
        pattern: The path to the attachment, as a SQLite pattern (to be
            passed to a LIKE clause).
        cursor: The Cursor object through which the SQLite queries are
            sent to the Zotero database.

    Returns:
        A list of (parentItemID, path) pairs that match the specified
        pattern. The returned list is empty if no matches are found.
    """
    query = 'SELECT parentItemID, path FROM itemAttachments WHERE path LIKE ?'
    cursor.execute(query, (pattern,))
    return list(cursor)


def select_attachment(pattern, cursor):
    """Prompt the user for the attachment that matches the pattern.

    Args:
        This function takes the same arguments as the find_attachments
        function.

    Returns:
        A (parentItemID, path) pair, None if no matches were found.
    """
    attachments = find_attachments(args.path, cursor)
    num_attachments = len(attachments)
    if num_attachments == 0:
        return None
    elif num_attachments == 1:
        return attachments[0]
    else:
        print('Found several attachments that match the specified pattern:')
        selection = pyzottk.simple_menu([path for _, path in attachments])
        return attachments[selection]


def add_metadata(istream, ostream, author, title):
    """Add author and title metadata to PDF file.

    Args:
        istream: the input PDF (string or stream in 'rb' mode)
        ostream: the output PDF (string or stream in 'wb' mode)
        author: the '/Author' metadata (string)
        title: the '/Title' metadata (string)
    """
    reader = PyPDF2.PdfFileReader(istream)
    writer = PyPDF2.PdfFileWriter()
    writer.appendPagesFromReader(reader)
    writer.addMetadata({'/Author': author,
                        '/Title': title})
    writer.write(ostream)


def setup_argument_parser():
    parser = ArgumentParser(description=__doc__,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('path', help=PATH_HELP)
    parser.add_argument('-o', '--output', help=OUTPUT_HELP)
    parser.add_argument('--data', help=DATA_HELP)
    parser.add_argument('--base', help=BASE_HELP)
    return parser


def sqlite_ro_connection(path):
    """Return a read-only connection to the SQLite database, if possible.

    This feature is only available as of Python 3.4.0. See
    https://docs.python.org/3.4/library/sqlite3.html#sqlite3.connect

    Args:
        path: The full path to the database.

    Returns:
        A ``Connection`` object.

    """
    major, minor = sys.version_info[0:2]
    if major >= 3 and minor >= 4:
        return sqlite3.connect('file:'+path+'?mode=ro', uri=True)
    else:
        return sqlite3.connect(path)


def attachment_absolute_path(path, base_attachment_path):
    """Returns the path to the specified attachment file.

    If base_attachment_path is None, then path must be a real path
    (absolute or relative). Otherwise, path must start with
    "attachments:", which is replaced with base_attachment_path to
    construct the full path. See

    https://www.zotero.org/support/preferences/advanced#linked_attachment_base_directory

    Args:
        path: The path column value in the itemAttachments Zotero table.
        base_attachment_path: The base directory for linked attachments,
            None if an absolute path is specified.

    Returns:
        The path to the attachment file.

    Raises:
        ValueError: base_attachment_path was not None for a stored
            attachment. Conversely, base_attachment_path was None for a
            linked attachment.
    """
    # TODO Allow for base_attachment_path is None
    if path.startswith(ATTACHMENTS_PREFIX):
        if path is None:
            raise ValueError('base_attachment_path should not be None for '
                             'linked attachments')
        tokens = path[len(ATTACHMENTS_PREFIX):].split('/')
        return os.path.join(base_attachment_path, *tokens)
    else:
        if path is not None:
            raise ValueError('base_attachment_path should be None for stored '
                             'attachments')
        return path


def default_output_name(input_name):
    """Return the default output name for the specified input name.

    This function is invoked when no ``--output`` option is specified
    (see the documentation of this option for further details).
    """
    tokens = os.path.split(input_name)
    basename = (tokens[-1][:-len(PDF_EXTENSION)]+WITH_METADATA+PDF_EXTENSION)
    return os.path.join(os.getcwd(), basename)


if __name__ == '__main__':
    args = setup_argument_parser().parse_args()

    if args.data:
        database_path = args.data
    else:
        path = pyzottk.prefs.select()
        if path:
            prefs = pyzottk.prefs.parse(path)
            database_path = os.path.join(prefs[DATA_DIR_KEY], 'zotero.sqlite')
        else:
            raise RuntimeError('could not locate Zotero preferences')

    connection = sqlite_ro_connection(database_path)
    cursor = connection.cursor()

    out = select_attachment(args.path, cursor)
    if out:
        parentItemID, path = out
    else:
        raise ValueError('No attachments match the specified pattern!')

    if path.startswith(ATTACHMENTS_PREFIX):
        if args.data:
            if args.base:
                base_attachment_path = args.base
            else:
                raise RuntimeError('Base attachment path must be specified.')
        else:
            base_attachment_path = prefs[BASE_ATTACHMENT_PATH_KEY]
    iname = attachment_absolute_path(path, base_attachment_path)
    oname = args.output or default_output_name(iname)

    fieldID = get_field_ID('title', cursor)

    with open(iname, 'rb') as istream, open(oname, 'wb') as ostream:
        add_metadata(istream, ostream,
                     get_authors(parentItemID, cursor),
                     get_title(parentItemID, cursor, fieldID))

    connection.close()

# Local Variables:
# fill-column: 72
# End:
