
Development
===========

To install the package for development, use

.. code-block::

    pip install --editable .

Building documentation
----------------------

In the folder ``docs``, run 

.. code-block::

    make clean; make html

to build the documentation. Make sure all dependencies from ``docs/environment.yml`` are installed. If the build succeeds, open ``docs/build/html/index.html`` in your browser.

Building for pypi
-----------------

.. code-block::

    python -m build

Upload:

.. code-block::
    
    python -m twine upload --repository pypi dist/*