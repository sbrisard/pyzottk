"""Helper functions for the pypdf2 module.
"""
import itertools

import PyPDF2


def is_destination(obj):
    """Return True if obj is an instance of PyPDF2.generic.Destination."""
    return isinstance(obj, PyPDF2.generic.Destination)


def copy_bookmarks(src, dest, outlines=None, parent=None):
    """Copy the bookmarks from src to dest.

    Args:
        src (PyPDF2.PdfFileReader): The source.
        dest (PyPDF2.PdfFileWriter): The destination.
        outlines (list of PyPDF2.generic.Destination): The outlines to be
            copied (for recursive calls). If None, then uses all elements
            returned by``src.getOutlines()``.
        parent (PyPDF2.generic.IndirectObject): The parent bookmark (if
            outlines are nested).
    """
    if outlines is None:
        outlines = src.getOutlines()
    for current, next in itertools.zip_longest(outlines, outlines[1:]):
        if is_destination(current):
            bookmark = dest.addBookmark(current.title,
                                        src.getDestinationPageNumber(current),
                                        parent=parent)
            if next and not is_destination(next):
                copy_bookmarks(src, dest, outlines=next, parent=bookmark)


def add_metadata(istream, ostream, author, title):
    """Add author and title metadata to PDF file.

    Args:
        istream: The input PDF (string or stream in 'rb' mode).
        ostream: The output PDF (string or stream in 'wb' mode).
        author: The '/Author' metadata (string).
        title: The '/Title' metadata (string).
    """
    reader = PyPDF2.PdfFileReader(istream)
    writer = PyPDF2.PdfFileWriter()
    writer.appendPagesFromReader(reader)
    writer.addMetadata({'/Author': author,
                        '/Title': title})
    copy_bookmarks(reader, writer)
    writer.write(ostream)
