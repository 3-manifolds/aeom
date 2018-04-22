#   Copyright (C) 2018-present Marc Culler, Nathan Dunfield and others.
#
#   This program is distributed under the terms of the 
#   GNU General Public License, version 2 or later, as published by
#   the Free Software Foundation.  See the file gpl-2.0.txt for details.
#   The URL for this program is
#     https://bitbucket.org/t3m/aeom
#   A copy of the license file may be found at:
#     http://www.gnu.org/licenses/old-licenses/gpl-2.0.html

class Pending(object):
    """
    An object of this class is returned by Asynchronizer.compute if the
    worker has not finished its computation yet.
    """
    def __init__(self, pid=-1):
        self.pid = pid

    def __repr__(self):
        return '<Pending computation in process %d>'%self.pid

