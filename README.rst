The aeom module provides the Asynchronizer class.  An Asynchronizer
object will evaluate methods of your favorite python object in a
separate worker process.  To do this you call the compute method of an
Asynchronizer with the name of the method in the form object.method
and, optionally, any args or kwargs to be passed to the method.
Subsequent calls to the compute method with the same parameters will
return the worker process until the worker process has finished the
computation, and the (cached) result thereafter.

The intended application is to allow a GUI application to do a CPU-bound
computation without becoming unresponsive.  Such an application can call
the compute method on a timer, e.g. using window.after in Tkinter, until
the answer has been computed.

This is a pure Python module which is published on PyPi and installable
with pip:

| pip install aeom

The source code is `here <https://bitbucket.org/t3m/async>`_.

License
========================

Copyright 2018-present by Marc Culler, Nathan Dunfield, and others.

All parts of this package are released under the
`GNU General Public License, version 2 <http://www.gnu.org/licenses/gpl-2.0.txt>`_
or (at your discretion) any later version as published by the Free
Software Foundation.
