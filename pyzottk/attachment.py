"""This module provides some functions to manage attachments."""
import os.path


PATH_PREFIX = 'attachments:'


def full_path(path, base_attachment_path):
    """Return the path to the specified attachment file.

    If base_attachment_path is None, then path must be a real path
    (absolute or relative). Otherwise, path must start with
    "attachments:", which is replaced with base_attachment_path to
    construct the full path. See

    https://www.zotero.org/support/preferences/advanced#linked_attachment_base_directory

    Args:
        path: The path column value in the itemAttachments Zotero table.
        base_attachment_path: The base directory for linked attachments,
            None if an absolute path is specified.

    Returns:
        The path to the attachment file.

    Raises:
        ValueError: base_attachment_path was not None for a stored
            attachment. Conversely, base_attachment_path was None for a
            linked attachment.
    """
    # TODO Allow for base_attachment_path is None
    if path.startswith(PATH_PREFIX):
        if path is None:
            raise ValueError('base_attachment_path should not be None for '
                             'linked attachments')
        tokens = path[len(PATH_PREFIX):].split('/')
        return os.path.join(base_attachment_path, *tokens)
    else:
        if path is not None:
            raise ValueError('base_attachment_path should be None for stored '
                             'attachments')
        return path
