"""Export PDF files attached to the items of a Zotero collection.

This script takes the name of a Zotero collection as an input. It then
lists all the items in this collection. For each of these items, it
retrieves the attached PDF file, and exports it to the specified
destination. The metadata (author and title) of the exported PDF file
are updated according to the item data.
"""
import configparser
import itertools
import os
import sys

import requests

from argparse import ArgumentParser, RawDescriptionHelpFormatter

from pyzottk.attachment import full_path
from pyzottk.pdf import add_metadata

BASE_URL = 'https://api.zotero.org'

BASE_ATTACHMENT_PATH_KEY = 'extensions.zotero.baseAttachmentPath'

COLLECTION_HELP = 'name of collection to export'

EXPORT_PATH_HELP = 'full path to export directory'

ITEMS_PER_REQUEST = 10

def parse_config():
    """Return the contents of the pyzottk configuration file.

    This function returns an instance of ``configparser.ConfigParser``.
    """
    home = os.path.expanduser('~')
    if sys.platform.startswith('darwin'):
        paths = [home, 'Library', 'Application Support', 'pyzottk']
    elif sys.platform.startswith('win32'):
        paths = [os.environ['APPDATA'], 'pyzottk']
    elif sys.platform.startswith('linux'):
        paths = [home, '.pyzottk']
    paths += ['pyzottk.cfg']
    path = os.path.join(*paths)
    if not(os.path.isfile(path)):
        raise RuntimeError('could not find config file: '+path)
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(*paths))
    return cfg


def setup_argument_parser():
    parser = ArgumentParser(description=__doc__,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('collection', help=COLLECTION_HELP)
    parser.add_argument('-o', '--output', help=EXPORT_PATH_HELP)
    return parser


def full_name(first_name, last_name):
    out = first_name
    if out != '' and last_name != '':
        out += ' '
    out += last_name
    return out


def get_collections(user_prefix, params, proxies):
    url = '/'.join([user_prefix, 'collections'])
    collections = []
    for i in itertools.count(0):
        r = requests.get(url=url, params=params, proxies=proxies)
        r_json = r.json()
        collections += r_json
        if len(r_json) < ITEMS_PER_REQUEST:
            params['start'] = 0
            return collections
        params['start'] += ITEMS_PER_REQUEST


if __name__ == '__main__':
    args = setup_argument_parser().parse_args()

    cfg = parse_config()
    user_prefix = '/'.join([BASE_URL, 'users', cfg['credentials']['user_id']])
    params = {'v': 3,
              'key': cfg['credentials']['key'],
              'format': 'json',
              'limit': ITEMS_PER_REQUEST,
              'start': 0}
    proxies = dict(cfg['proxies'])

    # Find key of exported collection
    url = '/'.join([user_prefix, 'collections'])
    collections = get_collections(user_prefix, params, proxies)
    collection_key = None
    params['start'] = 0

    while collection_key is None:
        r = requests.get(url=url, params=params, proxies=proxies)
        collections = r.json()
        for collection in collections:
            data = collection['data']
            if data['name'] == args.collection:
                collection_key = data['key']
                break
        params['start'] += ITEMS_PER_REQUEST
        if len(collections) < ITEMS_PER_REQUEST:
            break
    if collection_key is None:
        raise RuntimeError('could not find collection: '+args.collection)


    if args.output is None:
        args.output = os.path.join('.', args.collection)
        if not os.path.isdir(args.output):
            os.mkdir(args.output)

    # List items in collection
    url = '/'.join([user_prefix, 'collections', collection_key, 'items/top'])
    params['start'] = 0

    items = []
    while True:
        r = requests.get(url=url, params=params, proxies=proxies)
        new_items = list(r.json())
        items += new_items
        params['start'] += ITEMS_PER_REQUEST
        if len(new_items) < ITEMS_PER_REQUEST:
            break

    for i, item in enumerate(items):
        data = item['data']
        title = data['title']
        author = ', '.join(full_name(creator.get('firstName', ''),
                                     creator.get('lastName', ''))
                           for creator in data['creators'])
        print('[{}/{}] Exporting "{}" ({})'.format(i+1, len(items),
                                                   title, author))
        if item['meta']['numChildren'] >= 1:
            url = '/'.join([user_prefix, 'items', item['key'], 'children'])
            children = requests.get(url=url, params=params, proxies=proxies)
            for child in children.json():
                data = child['data']
                is_attachment = data['itemType'] == 'attachment'
                is_pdf = data.get('contentType', '') == 'application/pdf'
                if is_attachment and is_pdf:
                    iname = full_path(data['path'],
                                      cfg['local']['base_attachment_path'])
                    oname = os.path.join(args.output, os.path.basename(iname))
                    with open(iname, 'rb') as fi, open(oname, 'wb') as fo:
                        add_metadata(fi, fo, author, title)
