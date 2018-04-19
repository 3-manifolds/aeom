#   Copyright (C) 2018-present Marc Culler, Nathan Dunfield and others.
#
#   This program is distributed under the terms of the 
#   GNU General Public License, version 2 or later, as published by
#   the Free Software Foundation.  See the file gpl-2.0.txt for details.
#   The URL for this program is
#     https://bitbucket.org/t3m/aeom
#   A copy of the license file may be found at:
#     http://www.gnu.org/licenses/old-licenses/gpl-2.0.html
from . import Asynchronizer, Pending

# A test using a cpu-bound method of a SnapPy Manifold.
def simple_test():
    import snappy
    from time import sleep
    A = Asynchronizer()
    M = snappy.Manifold('14n2345')
    print('Computing Manifold("14n2345").covers(6) ...')
    for n in range(15):
        answer = A.compute(M.covers, args=(6,))
        print('working for %d seconds'%n if isinstance(answer, Pending) else answer)
        sleep(1)

if __name__ == '__main__':
    simple_test()
