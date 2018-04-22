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
def snappy_test():
    import snappy, time
    A = Asynchronizer()
    M = snappy.Manifold('K14n2345')
    degree = 6
    start = time.time()
    print('Starting asynchronous %s.covers(%d).'%(M, degree))
    A.compute(M.covers, degree)
    print('Starting %s.covers(%d) in the main process.'%(M, degree))
    answer1 = M.covers(degree)
    print('Main process finished at %.3f'%(time.time() - start))
    time.sleep(0.05)
    for n in range(30):
        print('Checking aeom at %.3f seconds'%(time.time() - start))
        answer2 = A.compute(M.covers, degree)
        if not isinstance(answer2, Pending):
            print('answer received at %.3f seconds'%(time.time()- start))
            break
        time.sleep(1)
    print(answer1)
    print(answer2)

def runtests():
    snappy_test()
    
if __name__ == '__main__':
    runtests()
