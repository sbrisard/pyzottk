"""This script adds call numbers to top-level items.

A preliminary, manual step is required: all items to be processed by
this script should be stored in a collection called ``no_call_number``
(the collection name is hard-coded).

Then, for each item in this collection, the script finds the path to the
attachment (if any). The call number is built from the directory that
contains the attachment. For example, if the path to the attachment is
``attachments:d/doe2017/filename.pdf``, then the call number reads:
``DOE2017`` (all upper case).

The script uses standard SQLite queries to the local database for read
only operations. The creation of call numbers is done through the web
API. Logging infos are stored in the file ``pyzottk.log``.
"""

import configparser
import datetime
import json
import logging
import os.path
import sqlite3

import requests


BASE_URL = 'https://api.zotero.org'


def call_number_from_path(path):
    return path.split('/')[-2].upper()


if __name__ == '__main__':
    logging.basicConfig(filename='pyzottk.log', level=logging.INFO)
    isonow = datetime.datetime.now().isoformat()
    logging.info('{} -- Creating missing call numbers'.format(isonow))

    cfg = configparser.ConfigParser()
    cfg.read('pyzottk.cfg')

    connection = sqlite3.connect(os.path.join(cfg['local']['data_directory'],
                                              'zotero.sqlite'))
    cursor = connection.cursor()

    # Find ID of collection that holds the items with no call number
    collectionName = 'no_call_number'
    query = 'SELECT collectionID FROM collections WHERE collectionName=?'
    cursor.execute(query, (collectionName,))
    collectionID = cursor.fetchone()[0]

    subquery = ('SELECT itemID FROM collectionItems '
                'WHERE collectionID = {}'.format(collectionID))
    query = ('SELECT items.itemID, items.key, items.version, '
             'itemAttachments.path '
             'FROM items INNER JOIN itemAttachments '
             'ON items.itemID = itemAttachments.parentItemID '
             'WHERE items.itemID IN ({})'.format(subquery))
    cursor.execute(query)

    key_to_callNumber_and_version = {k: (call_number_from_path(p), v)
                                     for _, k, v, p in cursor}

    num_call_numbers = len(key_to_callNumber_and_version)
    print('{} call numbers will be created'.format(num_call_numbers))

    connection.close()

    user_prefix = '/'.join([BASE_URL, 'users', cfg['credentials']['user_ID']])
    params = {'v': 3, 'key': cfg['credentials']['key'], 'format': 'json'}
    proxies = dict(cfg['proxies'])

    for key, (callNumber, version) in key_to_callNumber_and_version.items():
        url = '/'.join([user_prefix, 'items', key])
        data = {'callNumber': callNumber}
        headers = {'If-Unmodified-Since-Version': str(version)}
        r = requests.patch(url=url, data=json.dumps(data), headers=headers,
                           params=params, proxies=proxies)
        logging.info('{}: {}'.format(callNumber, r.status_code))

    logging.info('--------------------------------------------------')
