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
