"""This module provides functions to locate and parse the prefs.js file.
"""
import glob
import os.path
import re
import sys


def locate():
    """Return a list of ``prefs.js`` preference files.

    The profile directories are located according to the
    "Profile directory location"
    (https://www.zotero.org/support/kb/profile_directory) section in the
    Zotero documentation.
    """
    home = os.path.expanduser('~')
    if sys.platform.startswith('darwin'):
        paths = [home, 'Library', 'Application Support', 'Zotero', 'Profiles']
    elif sys.platform.startswith('win32'):
        paths = [os.environ['APPDATA'], 'Zotero', 'Zotero', 'Profiles']
    elif sys.platform.startswith('linux'):
        paths = [home, '.zotero', 'Profiles']
    paths += ['*', 'prefs.js']
    return glob.glob(os.path.join(*paths))


def select():
    """Prompt the user for the ``prefs.js`` preferences file to be used.

    If only one candidate is found, it is returned without any
    interaction with the user.

    Returns:
        The path to the ``prefs.js`` preferences file, None if no Zotero
        profiles were found.
    """
    from pyzottk import simple_menu
    candidates = locate()
    if len(candidates) == 0:
        return None
    elif len(candidates) > 1:
        prefix = os.path.commonpath(candidates)
        entries = ['$PROFILES'+c[len(prefix):] for c in candidates]
        print('Please select the Zotero preferences file:')
        print('($PROFILES = standard Zotero path to profiles):')
        print('')
        index = simple_menu(entries)
        return candidates[index]
    else:
        return candidates[0]


def parse(path):
    """Return the Zotero preferences in a dictionary

    Args:
        path: The path to the prefs.js preferences file.

    Returns:
        A dictionary of preferences.
    """
    prog = re.compile('^user_pref\("([a-zA-Z.]*)"\s*,\s*(.*)\);$')
    with open(path, 'r') as f:
        lines = (bytes(line, 'utf-8').decode('unicode_escape') for line in f)
        matches = (prog.match(line) for line in lines)
        prefs = {match.group(1): match.group(2).strip('"\'')
                 for match in matches if match}
        return prefs
