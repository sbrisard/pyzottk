"""This script renames attachments according to a consistent scheme.

For a top-level item with call number ``DOE2017``, the path to the
attachment should be ``attachments:d/doe2017/doe2017.pdf``.
"""
import configparser
import json
import os.path
import sqlite3

import requests

BASE_URL = 'https://api.zotero.org'
PATH_PREFIX = 'attachments:'


def expected_attachment_path(actual):
    elements = actual[len(PATH_PREFIX):].split('/')
    actname = elements[-1]
    _, ext = os.path.splitext(actname)
    expname = elements[-2]+ext

    return actual.replace(actname, expname)


def expand_path(path, base_attachment_path):
    elements = path[len(PATH_PREFIX):].split('/')
    return os.path.join(base_attachment_path, *elements)


if __name__ == '__main__':
    cfg = configparser.ConfigParser()
    cfg.read('pyzottk.cfg')

    connection = sqlite3.connect(os.path.join(cfg['local']['data_directory'],
                                              'zotero.sqlite'))
    cursor = connection.cursor()

    # First retrieve a list of (itemID, path) pairs:
    #
    #   - itemID: the ID of the attachment
    #   - path: the path to the attachment
    query = ('SELECT itemAttachments.itemID, itemAttachments.path '
             'FROM items INNER JOIN itemAttachments '
             'ON items.itemID = itemAttachments.parentItemID')
    cursor.execute(query)

    # Now build a list of itemID, path_old, path_new) triplets:
    #
    #   - itemID: the ID of the attachment
    #   - path_old: the actual path to the attachment
    #   - path_new: the expected path to the attachment
    #
    # Only th items for which these two paths differ are kept.
    items = []
    for itemID, path_actual in cursor:
        path_expected = expected_attachment_path(path_actual)
        if path_expected != path_actual:
            items.append((itemID, path_actual, path_expected))

    item_ID_to_paths = {item_ID: (path_old, path_new)
                        for item_ID, path_old, path_new in items}

    query = ('SELECT items.itemID, items.key, items.version '
             'FROM items WHERE items.itemID in ({})')
    cursor.execute(query.format(','.join(map(str, item_ID_to_paths.keys()))))

    # Now build a list of (key, version, path_old, path_new) tuples:
    #
    #   - key: the key of the attachment
    #   - version: the current version
    #   - path_old: the actual path to the attachment
    #   - path_new: the expected path to the attachment
    #
    # Only th items for which these two paths differ are kept.
    items = [(key, version, *item_ID_to_paths[item_ID])
             for item_ID, key, version in cursor]

    connection.close()

    base_attachment_path = cfg['local']['base_attachment_path']
    user_prefix = '/'.join([BASE_URL, 'users', cfg['credentials']['user_id']])
    params = {'v': 3, 'key': cfg['credentials']['key'], 'format': 'json'}
    proxies = dict(cfg['proxies'])

    for key, version, path_old, path_new in items:
        filename_old = path_old.split('/')[-1]
        filename_new = path_new.split('/')[-1]

        # Rename files locally
        path_old_exp = expand_path(path_old, base_attachment_path)
        path_new_exp = expand_path(path_new, base_attachment_path)
        # Uncomment this line if to actually perform the changes
        # os.rename(path_old_exp, path_new_exp)

        # Update database through the API
        url = '/'.join([user_prefix, 'items', key])
        data = {'title': filename_new,
                'path': path_new}
        headers = {'If-Unmodified-Since-Version': str(version)}
        # Uncomment this line if to actually perform the changes
        # r = requests.patch(url=url, data=json.dumps(data),
        #                    headers=headers, params=params, proxies)

        print('key:     {}'.format(key))
        print('version: {}'.format(version))
        print('title:   {}'.format(filename_new))
        print('old path: {}, {}'.format(path_old, path_old_exp))
        print('new path: {}, {}'.format(path_new, path_new_exp))
        print('')
        # print('status code: {}'.format(r.status_code))
