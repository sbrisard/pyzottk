"""Helper functions for the pypdf2 module.
"""
import PyPDF2


def add_metadata(istream, ostream, author, title):
    """Add author and title metadata to PDF file.

    Args:
        istream: the input PDF (string or stream in 'rb' mode)
        ostream: the output PDF (string or stream in 'wb' mode)
        author: the '/Author' metadata (string)
        title: the '/Title' metadata (string)
    """
    reader = PyPDF2.PdfFileReader(istream)
    writer = PyPDF2.PdfFileWriter()
    writer.appendPagesFromReader(reader)
    writer.addMetadata({'/Author': author,
                        '/Title': title})
    writer.write(ostream)
