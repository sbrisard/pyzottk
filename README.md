# pyzottk

A set of Python scripts I used to clean my [Zotero](https://www.zotero.org/)
library.

The project is organized as follows

  - ``scripts/``: this folder gathers scripts that have been cleaned-up and are
                  reusable,
  - ``sandbox/``: this folder gathers scripts/Jupyter notebooks that are not
                  really usable as such, but that I might use as later basis for
                  scripts.

Ultimately, some code will probably be factored out of the scripts into modules.

The recommended way to access Zotero libraries is through the
[Zotero API](https://www.zotero.org/support/dev/start). All scripts gathered
here do that through the [Requests](http://docs.python-requests.org/) module
(which must be installed). Zotero also offers
[direct access to the SQLite database](https://www.zotero.org/support/dev/client_coding/direct_sqlite_database_access),
which should be reserved to **read-only operations**. Since the Web API is slow,
using direct queries to the local database is the preferred method for read-only
operations here.

## List of available scripts

  - ``export_with_metadata``: add metadata to a PDF file attached to a Zotero
    item. This script requires the [PyPDF2](https://pythonhosted.org/PyPDF2/)
    module.