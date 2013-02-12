#! /usr/bin/env python
import sys

if __name__ == "__main__":
	mime_types=open("mime.types","r")

	header="""\
from collections import defaultdict
import generator

file_content=template.FileContentGen()
pyt_content=template.PYTContentGen()
rst_content=generator.RSTContentGen()

mime_types=defaultdict(lambda: ( 'text/plain' , file_content ) ) 

"""

	sys.stdout.write(header)
	for line in mime_types:
		line=line.strip()
		if len(line)>0 and not line.startswith('#'):
			line = line.split()
			mime_type=line[0]
			for ext in line[1:]:
				sys.stdout.write("mime_types['.%s']=( '%s' , file_content )\n"%(ext,mime_type))

	sys.stdout.write("mime_types['.pyt']=( 'text/html' , pyt_content )\n")
	sys.stdout.write("mime_types['.rst']=( 'text/html' , rst_content )\n")
	sys.stdout.write("mime_types['.rstex']=( 'application/x-latex' , rst_content )\n")
	mime_types.close()
