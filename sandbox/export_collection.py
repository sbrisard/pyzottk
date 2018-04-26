import configparser

import requests

import pyzottk

BASE_URL = 'https://api.zotero.org'

BASE_ATTACHMENT_PATH_KEY = 'extensions.zotero.baseAttachmentPath'


if __name__ == '__main__':
    path = pyzottk.prefs.select()
    if path:
        prefs = pyzottk.prefs.parse(path)
        print(prefs[BASE_ATTACHMENT_PATH_KEY])
    else:
        raise RuntimeError('could not locate Zotero preferences')

    cfg = configparser.ConfigParser()
    cfg.read('pyzottk.cfg')
    user_prefix = '/'.join([BASE_URL, 'users', cfg['credentials']['user_id']])
    params = {'v': 3, 'key': cfg['credentials']['key'], 'format': 'json'}
    proxies = dict(cfg['proxies'])

    collection_name = 'Emacs'

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
    for i in items.json():
        title = i['data']['title']
        author = ', '.join(c['firstName']+' '+c['lastName']
                           for c in i['data']['creators'])
        if i['meta']['numChildren'] >= 1:
            url = '/'.join([user_prefix, 'items', i['key'], 'children'])
            children = requests.get(url=url, params=params, proxies=proxies)
            for c in children.json():
                if (c['data']['itemType'] == 'attachment'
                    and c['data']['contentType'] == 'application/pdf'):
                    path = c['data']['path']
                    print(author+', '+title+', '+path)
