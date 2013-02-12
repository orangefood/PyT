import os
import stat
from datetime import datetime
from setuptools import setup

def read(fname):
	    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def most_recent_mod(directory):
	mod=0;
	for dirpath, dirnames, filenames in os.walk(directory): 
		for filename in filenames:
			stats=os.stat(os.path.join(dirpath,filename))
			mod=max(mod,stats[stat.ST_MTIME])
	return mod

src='src/of_pyt'

ver=datetime.fromtimestamp(most_recent_mod(src)).strftime('%Y.%m.%d.%H.%M')
setup(
#from of.xml import sxml 
#import of.util.collections as ofc 
	name='of_pyt',
	description='A very simple XML templeting system ',
	author='Robert I. Petersen',
	author_email='robert+oxml@orangefood.com', 
	version=ver, 
	package_dir={'of_pyt': src},
	packages=['of_pyt'], 
	license='GPL 2.0', 
	classifiers=[
'Development Status :: 4 - Beta',
'Intended Audience :: Developers',
'License :: OSI Approved :: GNU General Public License (GPL)',
'Programming Language :: Python',
'Topic :: Text Processing :: Markup :: XML'
	],
	long_description=read('README')
)
