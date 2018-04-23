import configparser

import requests

BASE_URL = 'https://api.zotero.org'

if __name__ == '__main__':
    cfg = configparser.ConfigParser()
    cfg.read('pyzottk.cfg')
    user_prefix = '/'.join([BASE_URL, 'users', cfg['credentials']['user_id']])
    params = {'v': 3, 'key': cfg['credentials']['key'], 'format': 'json'}
    proxies = dict(cfg['proxies'])

    collection_name = 'Emacs2'

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

    print(collection_key)
