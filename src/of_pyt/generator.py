import os
import sys
from of_xml import sxml 
from collections import defaultdict
import subprocess
import shlex
from . import LOG

WORK_DIR=None


def set_work(work):
	global WORK_DIR
	WORK_DIR=work

class PYTHandler(sxml.Handler):
	def __init__(self,out):
		self._o=out
		self._ident=['\t\t\t']
		self._code=False
		self._expression=False
		self._status="200 OK"
		self._headers={'Content-type':'text/html; charset=UTF-8'}

	def start_expression(self):
		self._o.write('"""%%_env.update_defaults(locals())\n%syield '%self._ident[-1])
		self._expression=True
	
	def end_expression(self):
		self._o.write('\n%syield """'%self._ident[-1])
		self._expression=False

	def start_python(self):
		self._o.write('"""%_env.update_defaults(locals())\n')
		self._code=True

	def end_python(self):
		self._o.write('\n%syield """'%self._ident[-1])
		self._code=False

	def indent(self,ndent='\t'):
		self._ident.append(self._ident[-1]+ndent)

	def unindent(self):
		self._ident.pop()

	def processing_instruction(self,pi,attributes): 
		self._o.write('<?')
		self._o.write(pi)
		if len(attributes)>0: self._o.write(' '+' '.join([ i[0]+'="'+i[1]+'"' for i in attributes.items()]))
		self._o.write(">")

	def doctype(self,doctype):
		self._o.write('<!DOCTYPE')
		self._o.write(doctype)
		self._o.write('>')

	def python(self,code):
		if code.startswith("="):
			self.start_expression()
			self._o.write('str(')
			self._o.write(code[1:])
			self._o.write(')')
			self.end_expression()
		elif code.startswith("$"):
			self._status=code[1:].strip()
		elif code.startswith(":"):
			[key,value]=code[1:].strip().split(':')
			self._headers[key.strip()]=value.strip()
		elif code.startswith("|"):
			include=code[1:].strip()
			c="_req=Request(request.environ.copy(),path_info=os.path.join( os.path.dirname(request.path_info),'%s'))\n"%include
			c=c+"_content=request.docstore.get_content( _req,include=True )\n"
			c=c+"if _content!=None: \n"
			c=c+"\tfor _b in _content._body(request,response) : yield _b\n"
			c=c+"else:\n"
			c=c+"\tyield '[ 404: include %s not found ]'\n\n"%include
			self.python(c)
		else:
			self.start_python()
			# unindent the else/elif clauses
			if not code.isspace():
				if code.startswith("else:") or code.startswith("elif:"):
					LOG.debug("else/elif unindent")
					self.unindent()

				#self._nocode=False
				for line in code.splitlines(True):
					self._o.write(self._ident[-1])
					self._o.write(line)
				if self._expression or line.isspace() or line.lstrip().startswith('#'):
					pass
				elif line.rstrip()[-1:]==':':
					# Indent after lines ending with ':'
					LOG.debug(" : indent")
					self.indent()
				else: 
					# Indent lines that are explicatly indented
					ndent=len(line)!=len(line.lstrip())
					if ndent>0:
						LOG.debug(" explicate indent")
						self.indent(line[:len(line)-len(line.lstrip())])
			else:
				LOG.debug("blank line unindent")
				self.unindent()
			self.end_python()

	def open(self,tag,attributes):
		if self._code or self._expression: raise AssertionError("a tag found in code or expression near line %d, column %d"%(self.parser.line,self.parser.col))
		else:
			self._o.write('<')
			self._o.write(tag)
			if len(attributes)>0: self._o.write(' '+' '.join([ i[0]+'="'+i[1]+'"' for i in attributes.items()]))
			self._o.write('>')

	def close(self,tag): 
		self._o.write('</%s>'%tag)

	def empty(self,tag,attributes):
		if self._code or self._expression: raise AssertionError("a tag found in code or expression near line %d, column %d"%(self.parser.line,self.parser.col))
		else:
			self._o.write('<')
			self._o.write(tag)
			if len(attributes)>0: self._o.write(' '+' '.join([ i[0]+'="'+i[1]+'"' for i in attributes.items()]))
			self._o.write("/>")

	def text(self,text):
		self._o.write(text.replace('"""','\\"""'))
	
	def cdata(self,cdata):
		self._o.write("<![CDATA[%s]]>"%cdata)

	def comment(self,comment):
		self._o.write("<!--%s-->"%(comment,))

class PYTContentGen(object):
	def __init__(self):
		pass

	def get_content(self,pyt_tmpl,mimetype,include=False):
		py_src=self.get_source(pyt_tmpl)
		dir=os.path.dirname(py_src)
		if not os.path.exists(dir):
			os.makedirs(dir)
		src_file=open(py_src,'w')
		self.render_python(pyt_tmpl,py_src)
		src_file.close()
		content=self.compile_python(py_src)
		return content

	def get_source(self,path):
		return os.path.abspath(self.get_python_name(os.path.join(WORK_DIR,'pyt',path[1:])))
		
	def get_python_name(self,fname):
		return os.path.splitext(fname)[0]+'.py'

	def compile_pyt(self,pyt,out=sys.stdout):
		h=PYTHandler(out)
		p=sxml.Parser(h)
		p.addPassthrough('@','@',h.python)
		h.end_python()
		p.parse(pyt)
		h.start_python()
		return (h._status,h._headers)

	def compile_python(self,py,py_filename='<file>'):
		if type(py)==str:
			if py.endswith('.py'):
				py_file=open(py)
				code=compile(py_file.read(),py,'exec')
				py_file.close()
			else:
				code=compile(py,'<string>','exec')
		else:
			code=compile(py.read(),py_filename,'exec')
		loc={}
		exec code in loc 
		return loc['source']

	def render_python(self,pyt,out=None):
		close_out=False
		close_pyt=False
		if out==None:
			out=open(self.get_python_name(pyt),'w')
			close_out=True
		elif type(out)==str:
			out=open(out,'w')
			close_out=True

		if type(pyt)==str:
			pyt=open(pyt)
			close_pyt=True

		header="""\
import sys
import os.path
import of_util.collections as _ofc
from of_pyt import LOG
from webob import Request

class Content(object):
	def _body(self, request,response ):
		# Use a dotdict to dereference things like request.environ.PATH_INFO
		_env=_ofc.dotdict(locals())
		try:
"""

		footer="""\
		except:
			excinfo=sys.exc_info()
			LOG.error("Error processing %%s"%%request.path_info,exc_info=excinfo)
			yield 'An unexpected error has occured, please notify the server administartor.  This problem has been logged\\n'
			yield '<!-- (line:%%s) %%s: %%s -->'%%(excinfo[2].tb_lineno,excinfo[0].__name__,excinfo[1])

	def __call__(self,req,res):
		res.headers.update(self._headers)
		res.status=self._status
		res.app_iter=self._body(req,res)

	def __init__(self):
		self._status='%s'
		self._headers=%s

source=Content()
"""
		out.write(header)
		stat_head=self.compile_pyt(pyt,out)
		out.write(footer%stat_head)

		if close_out: out.close()
		if close_pyt: pyt.close()

class FileContent(object):
	def __init__(self,path,headers):
		self._path=path;
		self._headers=headers
		   
	def __call__(self, req, res):
		res.headers.update(self._headers)
		res.status=200
		res.app_iter=self._body(req,res)
	
	def _body(self,req,res):
		f = open(self._path,'r')
		for line in f:
			yield line
		f.close()

class FileContentGen(object):
	def __init__(self):
		pass

	def get_content(self,path,mimetype,include=False):
		return FileContent(path,[('Content-type',mimetype)])

RSTWRITERS=defaultdict(lambda:"html")
RSTWRITERS['test/html']='html'
RSTWRITERS['application/x-latex']='latex'
RSTEXT=defaultdict(lambda: '.html')
RSTEXT['html']='.html'
RSTEXT['latex']='.tex'

class RSTContentGen(object):
	def __init__(self):
		pass

	def get_out(self,path,writer,include):
		return os.path.abspath(self.get_out_name(os.path.join(WORK_DIR,'rst',path[1:]),writer,include))

	def get_out_name(self,fname,writer,include):
		return os.path.splitext(fname)[0]+('.incl' if include else '')+RSTEXT[writer]

	def get_content(self,rst,mimetype,include=False):
		import docutils.core
		writer=RSTWRITERS[mimetype]
		out=self.get_out(rst,writer,include)
		dir=os.path.dirname(out)
		if not os.path.exists(dir):
			os.makedirs(dir)
		source=open(rst)
		dest=open(out,"w")
		if include:
			dest.write(docutils.core.publish_parts(source.read(),writer_name=writer)['body'])
			dest.flush()
		else:
			docutils.core.publish_file(source=source,destination=dest,writer_name=writer)
		source.close()
		dest.close()
		return FileContent(out,[('Content-type',mimetype)])

class RSTPDFContentGen(object):
	def __init__(self):
		pass

	def get_tex(self,path):
		return os.path.abspath(self.get_tex_name(os.path.join(WORK_DIR,'rstpdf',path[1:])))

	def get_tex_name(self,fname):
		return os.path.splitext(fname)[0]+'.tex'
	
	def get_pdf_name(self,fname):
		return os.path.splitext(fname)[0]+'.pdf'

	def get_content(self,rst,mimetype,include=False):
		import docutils.core
		writer='latex'
		tex=self.get_tex(rst)
		pdf=self.get_pdf_name(tex)
		dir=os.path.dirname(tex)
		if not os.path.exists(dir):
			os.makedirs(dir)

		# Compile the rst to latex
		source=open(rst)
		dest=open(tex,"w")
		docutils.core.publish_file(source=source,destination=dest,writer_name=writer)
		source.close()
		dest.close()
		# Compile te latex to PDF
#TODO: make sure this is safe, maybe the face that the file exists is good enough?
#TODO: also in Popen shell=False by default
		tex_file=os.path.basename(tex)
		cmd='pdflatex %s'%tex_file
		cmd=cmd.encode() # switch from unicode to ascii
		p = subprocess.Popen(shlex.split(cmd),cwd=dir)
		p.wait()
		p = subprocess.Popen(shlex.split(cmd),cwd=dir)
		p.wait()
		return FileContent(pdf,[('Content-type',mimetype)])
	
