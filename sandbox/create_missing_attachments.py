"""This script creates linked attachments to parent items.

The script locates all top-level items that have a call number, but no
attachments. For each of these items, the script then attempts to find
a local file (by default, *.pdf) that matches the item, and create a
linked attachment to this file in the Zotero library.

The call number of the top-level item being "DOE2017", the attached
file is searched for locally as follows.

  1. Search for files that match a specified pattern (by default,
     "*.pdf") in the local directory "base_attachment_path/d/doe2017/",
     where base_attachment_path is specified by the user.
  2. If exactly one file matching the pattern is found in this
     directory, then a linked attachment is created to this file.
  3. Otherwise, nothing is done to the top-level item.

All parameters of the script must be specified through the pyzottk.cfg
config file. Its structure is given below:

    [credentials]
    key =
    user_ID =

    [local]
    data_directory =
    base_attachment_path =

    [proxies]
    http =
    https =

"""
import configparser
import datetime
import glob
import itertools
import logging
import os.path

import requests

BASE_URL = 'https://api.zotero.org'


class MyException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return str(self.msg)


class NoChildrenException(MyException):
    pass


class TooManyChildrenException(MyException):
    pass


def get_children(item_key, user_ID, key, proxies):
    """Return the list of children of a specified Zotero item.

    The function returns the keys to all children.
    """
    params = {'v': '3', 'key': key, 'format': 'json'}
    url = '/'.join([BASE_URL, 'users', user_ID,
                    'items', item_key, 'children'])
    return [i['key']
            for i in requests.get(url, params, proxies=proxies).json()]


def locate_child(call_number, base_attachment_path, pattern='*.pdf'):
    """Return path to a linked attachement to a Zotero item.

    The function tries to locate a file that matches the pattern in the
    following directory

        base_attachment_path/first_letter_of_call_number/call_number/

    Args:
        call_number: The call number of the parent item, as stored in
            the Zotero library.
        base_attachment_path: The root directory of all attachments.
        pattern: The pattern that candidate children must match in the
            search path.

    Returns:
        The relative path to the candidate child, as a "/"-separated
        string,  stripped of base_attachment_path, and prefixed with
        "attachments:".

    Raises:
        NoChildrenException: No file matching the pattern is found.
        TooManyChildrenException: More than one file matching the
            pattern is found.
    """
    path = os.path.join(base_attachment_path, call_number[0], call_number,
                        pattern)
    children = glob.glob(path)
    if len(children) == 0:
        raise NoChildrenException(call_number)
    elif len(children) >= 2:
        raise TooManyChildrenException(call_number)
    else:
        return ('attachments:' + '/'.join((call_number[0],
                                           call_number,
                                           os.path.basename(children[0]))))


def create_attachments(items, user_ID, key, proxies):
    """Return the result of a POST request that creates linked attachments.

    Args:
        items: A list of attachments to be created. Each item of the
            list is a tuple (parent_item, path, title).
        user_ID: The user's Zotero ID.
        key: The user's API key.
        proxies: A dictionnary to be used by the requests module.

    Returns:
        The POST request.
    """
    params = {'v': '3',
              'key': key,
              'format': 'json',
              'itemType': 'attachment',
              'linkMode': 'linked_file'}
    template = requests.get(BASE_URL+'/items/new',
                            params=params,
                            proxies=proxies).json()
    data = []
    for parent_item, path, title in items:
        item = template.copy()
        item['contentType'] = 'application/pdf'
        item['parentItem'] = parent_item
        item['path'] = path
        item['title'] = title if title else os.path.basename(path)
        data.append(item)
    # return requests.post(BASE_URL+'/users/'+user_ID+'/items/',
    #                      data=json.dumps(data),
    #                      params=params,
    #                      proxies=proxies)
    return None


def add_missing_attachments(start, limit, user_ID, key, proxies,
                            base_attachment_path):
    """
    Add attachments to the specified Zotero items, if missing.

    For the exact meaning of start and limit, see

        https://www.zotero.org/support/dev/web_api/v3/basics#sorting_and_pagination

    Args:
        start: The index of the first Zotero item to be retrieved.
        limit: The number of Zotero items to be retrieved.
        user_ID: The user's Zotero ID.
        key: The user's API key.
        proxies: A dictionnary to be used by the requests module.
        base_attachment_path: The root directory of all attachments.

    Returns:
        The number of attachments created, and the POST request that was
        sent.
    """
    # Retrieve items to be updated
    print('Updating attachments for items {} to {}'.format(start,
                                                           start+limit-1))
    params = {'v': '3',
              'key': key,
              'format': 'json',
              'include': 'data',
              'sort': 'creator',
              'limit': str(limit),
              'start': str(start)}
    url = '/'.join([BASE_URL, 'users', user_ID, 'items', 'top'])
    items = requests.get(url, params, proxies=proxies).json()

    new_items = []
    for item in items:
        data = item['data']
        parent_item = data['key']
        if get_children(parent_item, user_ID, key, proxies) == []:
            call_number = data['callNumber'] if 'callNumber' in data else ''
            if call_number:
                call_number = data['callNumber'].lower()
                try:
                    path = locate_child(call_number, base_attachment_path)
                    new_items.append((parent_item, path, None))
                    logging.info('Found child for '+call_number+': '+path)
                except NoChildrenException as e:
                    logging.warning('No children found for '+call_number)
                except TooManyChildrenException as e:
                    logging.warning('Too many children found for '+call_number)
            else:
                logging.warning('No call number for item: '+data['title'])
    return len(items), create_attachments(new_items)


def get_items(user_ID, key, proxies):
    """Return a list of all items in the Zotero database."""
    limit = 100
    params = {'v': '3',
              'key': key,
              'format': 'json',
              'include': 'data',
              'sort': 'creator',
              'limit': str(limit)}
    url = '/'.join([BASE_URL, 'users', user_ID, 'items', 'top'])
    items = []
    for start in itertools.count(step=100):
        params['start'] = str(start)
        r = requests.get(url, params, proxies=proxies).json()
        items += r
        if len(r) < limit:
            break
        print(start, len(r))
    return items


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('pyzottk.cfg')

    user_ID = config['credentials']['user_ID']
    key = config['credentials']['key']
    base_attachment_path = config['local']['base_attachment_path']
    proxies = config['proxies']

    logging.basicConfig(filename='pyzotclean.log',
                        level=logging.INFO)
    isonow = datetime.datetime.now().isoformat()
    logging.info('{} -- Updating attachments'.format(isonow))
    limit = 50
    for start in itertools.count(step=limit):
        num_items, request = add_missing_attachments(start, limit,
                                                     user_ID, key, proxies,
                                                     base_attachment_path)
        if num_items < limit:
            break
    logging.info('--------------------------------------------------')
