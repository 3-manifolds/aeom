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
from . import Asynchronizer, Pending

# A test using a cpu-bound method of a SnapPy Manifold.
def snappy_test():
    import snappy, time
    A = Asynchronizer()
    M = snappy.Manifold('K14n2345')
    degree = 6
    print('Starting asynchronous %s.covers(%d).'%(M, degree))
    start = time.time()
    A.compute(M.covers, degree)
    print('Starting %s.covers(%d) in the main process.'%(M, degree))
    answer1 = M.covers(degree)
    done = time.time()
    print('Main process finished at %.3f.'%(done - start))
    time.sleep(0.05)
    for n in range(30):
        print('Checking aeom at %.3f seconds'%(time.time() - start))
        answer2 = A.compute(M.covers, degree)
        if not isinstance(answer2, Pending):
            print('answer received at %.3f seconds'%(time.time()- start))
            break
        time.sleep(1)
    A.stop()
    print(answer1)
    print(answer2)

def volume_test():
    import snappy, time
    A = Asynchronizer()
    for M in snappy.OrientableCuspedCensus[:300]:
        try:
            while True:
                result = A.compute(M.volume)
                if not isinstance(result, Pending):
                    break
                time.sleep(0.2)
            print(M, 'OK' if abs(float(M.volume()) - float(result)) < 10**-13 else 'FAILED')
        except Exception as e:
            print(M, e)
    A.stop()
    
def runtests():
    snappy_test()
    volume_test()
    
if __name__ == '__main__':
    runtests()
