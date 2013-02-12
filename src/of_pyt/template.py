from mime_types import mime_types
import fnmatch
import os
import time
from generator import set_work

from . import LOG

class DocumentStore(object):
	def __init__(self,work,check_mod=True):
		global TEMP_DIR
		set_work(os.path.join(work,'pyt_templating'))
		self._check_mod=check_mod
		self._cache={}

#	def get_error(self,error):
#		path=self._err+"/%03d.pyt"%error 
#		if not os.path.exists( self.get_file( path ) ):
#			path=self._err+"/%03d.html"%error 
#
#		return self.get_content( path )
#			
#	def get_file(self,path):
#		f=os.path.abspath(os.path.join(self._html,path[1:]))
#		if os.path.isdir(f):
#			for ndx in self._directory_index:
#				ndx_file=os.path.join(f,ndx)
#				if os.path.isfile(ndx_file):
#					f=ndx_file
#					break
#
#		if os.path.isdir(f) and self._indexer!=None:
#			f=os.path.abspath(os.path.join(self._html,self._indexer))
#
#		return f

	def get_docs(self,html,*patterns):
		return reduce( lambda a,b: a+b, 
		[ 
			[
			os.path.join(dirpath,filename)[len(html):] for filename in filenames 
			if [fnmatch.fnmatch(filename,pattern) for pattern in patterns].count(True)>0 
			] 
			for dirpath,dirnames,filenames in os.walk(html) 
		])

#	def get_content(self,path,mime_type=None,generator=None,include=False):
	def get_content(self,src,mime_type=None,generator=None,include=False):
#		if not isinstance(path,str):
#			if hasattr(path,'path_info'):
#				path=path.path_info
#			elif isinstance(path,dict) and 'PATH_INFO' in path:
#				path=path['PATH_INFO']
		content=None
#		src=self.get_file(path)
		key=src if not include else '[include]'+src
#		LOG.debug("content request: %s"%path);
		LOG.debug("source file: %s"%src);
		LOG.debug("cache key: %s"%key);

		if os.path.isfile(src):
			if key in self._cache:
				LOG.debug("src content '%s' found in cache with key %s"%(src,key));
				(t,c)=self._cache[key]
				if not self._check_mod or os.stat(src).st_mtime<t:
					content=c

			if content==None:
				LOG.debug("src content '%s' not found in cache with key %s"%(src,key));
				ext=os.path.splitext(src)[1]
				(mimetype,content_generator)=mime_types[ext]
				if mime_type==None: mime_type=mimetype
				if generator==None: generator=content_generator
				content=generator.get_content(src,mime_type,include)
				self._cache[key]=(time.time(),content)

		return content
