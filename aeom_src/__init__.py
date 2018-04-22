#   Copyright (C) 2018-present Marc Culler, Nathan Dunfield and others.
#
#   This program is distributed under the terms of the 
#   GNU General Public License, version 2 or later, as published by
#   the Free Software Foundation.  See the file gpl-2.0.txt for details.
#   The URL for this program is
#     https://bitbucket.org/t3m/aeom
#   A copy of the license file may be found at:
#     http://www.gnu.org/licenses/old-licenses/gpl-2.0.html

from __future__ import print_function
from .version import __version__
from .asynchronizer import Asynchronizer
from .pending import Pending
import sys

assert sys.version_info.major > 2, 'Sorry, aeom requires Python 3.'

__all__ = ['Asynchronizer', 'Pending']
