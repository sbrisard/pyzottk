"""Export PDF files attached to the items of a Zotero collection.

This script takes the name of a Zotero collection as an input. It then
lists all the items in this collection. For each of these items, it
retrieves the attached PDF file, and exports it to the specified
destination. The metadata (author and title) of the exported PDF file
are updated according to the item data.
"""
import configparser
import os
import sys

import requests

from argparse import ArgumentParser, RawDescriptionHelpFormatter

from pyzottk.attachment import full_path
from pyzottk.pdf import add_metadata

BASE_URL = 'https://api.zotero.org'

BASE_ATTACHMENT_PATH_KEY = 'extensions.zotero.baseAttachmentPath'

COLLECTION_HELP = 'The name of the collection to be exported.'

EXPORT_PATH_HELP = 'The path to the directory in which the files are to be exported.'

def config_file_path():
    """Return the default path to the config file."""
    home = os.path.expanduser('~')
    if sys.platform.startswith('darwin'):
        paths = [home, 'Library', 'Application Support', 'pyzottk']
    elif sys.platform.startswith('win32'):
        paths = [os.environ['APPDATA'], 'pyzottk']
    elif sys.platform.startswith('linux'):
        paths = [home, '.pyzottk']
    paths += ['pyzottk.cfg']
    return os.path.join(*paths)


def setup_argument_parser():
    parser = ArgumentParser(description=__doc__,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('collection', help=COLLECTION_HELP)
    parser.add_argument('-o', '--output', default='.', help=EXPORT_PATH_HELP)
    return parser


if __name__ == '__main__':
    args = setup_argument_parser().parse_args()

    cfg = configparser.ConfigParser()
    cfg.read(config_file_path())
    user_prefix = '/'.join([BASE_URL, 'users', cfg['credentials']['user_id']])
    params = {'v': 3, 'key': cfg['credentials']['key'], 'format': 'json'}
    proxies = dict(cfg['proxies'])

    # Find key of exported collection
    url = '/'.join([user_prefix, 'collections'])
    r = requests.get(url=url, params=params, proxies=proxies)
    collection_key = None
    for item in r.json():
        data = item['data']
        if data['name'] == args.collection:
            collection_key = data['key']
            break
    else:
        raise RuntimeError('Could not find collection: {}'.format(args.collection))

    # List items in collection
    url = '/'.join([user_prefix, 'collections', collection_key, 'items/top'])
    items = requests.get(url=url, params=params, proxies=proxies)

    # Export items
    for item in items.json():
        data = item['data']
        title = data['title']
        author = ', '.join(creator['firstName']+' '+creator['lastName']
                           for creator in data['creators'])
        if item['meta']['numChildren'] >= 1:
            url = '/'.join([user_prefix, 'items', item['key'], 'children'])
            children = requests.get(url=url, params=params, proxies=proxies)
            for child in children.json():
                data = child['data']
                is_attachment = data['itemType'] == 'attachment'
                is_pdf = data['contentType'] == 'application/pdf'
                if is_attachment and is_pdf:
                    iname = full_path(data['path'],
                                      cfg['local']['base_attachment_path'])
                    oname = os.path.join(args.output, os.path.basename(iname))
                    with open(iname, 'rb') as fi, open(oname, 'wb') as fo:
                        add_metadata(fi, fo, author, title)
