import os, sys, sysconfig
from setuptools import setup, Command
from aeom_src.version import __version__
from aeom_src import Asynchronizer
long_description = Asynchronizer.__doc__

class AeomTest(Command):
    user_options = []
    def initialize_options(self):
        pass 
    def finalize_options(self):
        pass
    def run(self):
        sys.path.insert(0, 'build/lib')
        import aeom.test
        aeom.test.runtests()

# To make python3 setup.py test work on Windows we need this.
if __name__ == '__main__':
    setup(name='aeom',
        version=__version__,
        packages=['aeom'],
        package_dir = {'aeom': 'aeom_src'}, 
        package_data={},
        python_requires='>=3',
        install_requires=['future'],
        entry_points = {},
        cmdclass =  {'test' : AeomTest},
        zip_safe = True,
        description='An object which evaluates methods asynchronously', 
        long_description = long_description,
        author = 'Marc Culler and Nathan M. Dunfield',
        author_email = 'culler@uic.edu, nathan@dunfield.info',
        license='GPLv2+',
        url = 'https://bitbucket.org/t3m/aeom',
        classifiers = [
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Topic :: Software Development :: Libraries :: Python Modules',
        ],
        keywords = 'asynchronous, worker',
    )
