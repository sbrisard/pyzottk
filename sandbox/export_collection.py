import configparser
import os.path

import requests

from pyzottk.pdf import add_metadata

BASE_URL = 'https://api.zotero.org'

BASE_ATTACHMENT_PATH_KEY = 'extensions.zotero.baseAttachmentPath'


if __name__ == '__main__':
    collection_name = 'Emacs'
    export_path = '.'

    cfg = configparser.ConfigParser()
    cfg.read('pyzottk.cfg')
    user_prefix = '/'.join([BASE_URL, 'users', cfg['credentials']['user_id']])
    params = {'v': 3, 'key': cfg['credentials']['key'], 'format': 'json'}
    proxies = dict(cfg['proxies'])

    # Find key of exported collection
    url = '/'.join([user_prefix, 'collections'])
    r = requests.get(url=url, params=params, proxies=proxies)
    collection_key = None
    for item in r.json():
        data = item['data']
        if data['name'] == collection_name:
            collection_key = data['key']
            break
    else:
        raise RuntimeError()

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
                    oname = os.path.join(export_path, os.path.basename(iname))
                    with open(iname, 'rb') as fi, open(oname, 'wb') as fo:
                        add_metadata(fi, fo, author, title)
