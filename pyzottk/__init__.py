"""pyzottk is a module that allows interaction with Zotero libraries.
"""
import pyzottk.prefs


def simple_menu(entries, msg=None):
    """Display a list of choices and prompt for the user's selection.

    This function loops indefinitely, until a valid selection is
    entered.

    Args:
        entries: An iterable of entries that can be selected.
        msg: The prompt message.

    Returns:
        The index of the user's selection.

    Raises:
        ValueError: entries is an iterator, while a container was
                    expected.
    """
    if iter(entries) is iter(entries):
        raise ValueError('entries should be a container, not an iterator')
    entries = list(entries)
    num_entries = len(entries)
    num_digits = len(str(num_entries-1))
    for index, entry in enumerate(entries):
        index_str = '[{0}]'.format(index).rjust(num_digits+2)
        print(index_str+' '+entry)

    err_msg = 'Selection n must be such that: 0 <= n < {}!'.format(num_entries)
    while True:
        try:
            selection = int(input(msg or ''))
            if selection >= 0 and selection < len(entries):
                break
        except ValueError:
            pass
        print(err_msg)
    return selection
