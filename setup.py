import os, sys, sysconfig
from setuptools import setup, Command
from aeom_src.version import __version__
from aeom_src import Asynchronizer
long_description = Asynchronizer.__doc__

def distutils_dir_name(dname):
    """Returns the name of a distutils build subdirectory"""
    name = "build/{prefix}.{plat}-{ver[0]}.{ver[1]}".format(
        prefix=dname, plat=sysconfig.get_platform(), ver=sys.version_info)
    if dname == 'temp' and sys.platform == 'win32':
        name += os.sep + 'Release'
    return name
        
def build_lib_dir():
    if sys.version_info.major == 2:
        return os.path.abspath(distutils_dir_name('lib'))
    else:
        return os.path.abspath('./build/lib')
                               
class AeomTest(Command):
    user_options = []
    def initialize_options(self):
        pass 
    def finalize_options(self):
        pass
    def run(self):
        print('testing aeom in %s'%build_lib_dir())
        sys.path.insert(0, build_lib_dir())
        import aeom.test
        aeom.test.runtests()

install_requires = ['future']
if sys.version_info.major == 2:
    install_requires.append('dill')
    
# To make python3 setup.py test work on Windows we need this.
if __name__ == '__main__':
    setup(name='aeom',
          version=__version__,
          packages=['aeom'],
          package_dir = {'aeom': 'aeom_src'}, 
          package_data={},
          install_requires=install_requires,
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
