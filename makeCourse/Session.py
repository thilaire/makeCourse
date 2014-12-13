""" Possible template variable

- Filename : name of the file
- type : type of the session
- name : name of the session
- Date : execution date

"""


from bs4 import Comment, NavigableString
import io
import jinja2
from jinja2 import meta
import os
import time
from hashlib import md5
from colorama import Fore, Style
import datetime
from .osUtils import runCommand, getPathTime, splitToComma
from .config import Config


# jinja renderer (change the default delimiters used by Jinja such that it won't pick up brackets attached to LaTeX macros.)
# cfhttp://tex.stackexchange.com/questions/40720/latex-in-industry
renderer = jinja2.Environment(
                        block_start_string = '{<',
                        block_end_string = '>}',
                        comment_start_string='{%<',
                        comment_end_string='>%}',
                        variable_start_string = '{{<',
                        variable_end_string = '>}}',
                        loader = jinja2.FileSystemLoader( os.path.abspath('.') )
                )


def containsTextOnly( tag):
	return tag.string and not tag.find_all()


class Session(object):

	number = 0		# number of objects created

	def __init__(self, tag, commonFiles):
		"""
		- tag (beautifulSoup object) to build the session
		- dictionary of commonFiles
		"""
		type(self).number += 1
		self.tag = tag															# beautifulSoup tags
		self.type = type(self).__name__											# name of the type of Session
		self.commonFiles = commonFiles[ self.type ]								# common files to be included/copied

		# build dictonary of attributes and contains-text-only tags
		self.dict = {}
		for p in tag.parents:	# build self.dict from the parents
			if p is not None:
				self.dict = dict( {tag.name:tag.string for tag in p( containsTextOnly, recursive=False) }, **self.dict )

		self.dict.update( {tag.name:tag.string for tag in self.tag( containsTextOnly, recursive=False) } )
		self.dict.update( tag.attrs)

		self.dict [ 'type' ] = self.type
		self.name = tag.get('name') or self.dict.get('name') or self.type+str(type(self).number) 		# name of the Session (usually type+number)
		self.dict[ 'name' ] = self.name
		self.remainsUnchanged = False

		#contents
		self.dict[ 'Content' ] = '\n'.join( [l for l in self.tag.contents if isinstance(l,NavigableString) and not isinstance(l,Comment)] )

	def make(self, options):
		pass

	def files(self):
		pass


	def shouldBeMake(self, scheme):
		"""determine if the unit should be make
		(the documents of the units should be produced)
		(if the previously produced files are older than the files necessary to build the unit, then we should make the unit
		"""
		if self.remainsUnchanged:
			# get the time of the oldest produced file (if the file exist)
			oldestTimeProducedFile = time.time()
			for f in self.files():
				target = scheme.format( **self.dict ) + f
				targetTime = os.path.getmtime(target) if os.path.exists(target) else 0
				if oldestTimeProducedFile>targetTime:
					oldestTimeProducedFile = targetTime
			# get the time of all the possible files
			importedFiles = splitToComma( self.tag["imported"] )
			pathTimes = [ getPathTime(os.path.dirname(p.strip())) for p in importedFiles ]
			if pathTimes and self.tag["imported"]:
				newestTimeParts = max( pathTimes )
			else:
				newestTimeParts = 0

			return (newestTimeParts > oldestTimeProducedFile)
		else:
			 return True


	def prepareResources(self, dest):
		"""Prepare (copy) the resources (commonFiles) of a session into the dest folder (temporary or debug) """
		runCommand( ['cp', self.commonFiles+'*', dest])
		done = {}
		for p in splitToComma( self.tag.get("imported",'') ):
			pPath = '/'.join(p.strip().split('/')[0:-1])
			if pPath not in done:
				runCommand( ['cp', '-R', pPath+"/", dest])
				done[ pPath ]=True



	def writeFileFromTemplate(self, templateFileName, fileName, dictionary={}, encoding='utf-8'):
		"""Read the template file, and fill it with the dictionnary (and the content of the session, of course)
		and save it in the temporary directory
		"""

		#open the template file
		template = renderer.get_template( self.commonFiles+templateFileName, encoding)
		# dictionary for the template file
		d = dict( dictionary, **self.dict)		# http://stackoverflow.com/questions/1781571/how-to-concatenate-two-dictionaries-to-create-a-new-one-in-python
		d["Filename"] = fileName
		now = datetime.datetime.now()
		d['Date'] = now.strftime('%d/%m/%Y - %H:%M')
		#create the new file
		resultFile = io.open( fileName, "w", encoding=encoding)
		t=template.render( d )
		resultFile.write( t )
		resultFile.close()

		# get the list of unused variables
		# cf http://stackoverflow.com/questions/8260490/how-to-get-list-of-all-variables-in-jinja-2-templates
		template_source = renderer.loader.get_source(renderer, self.commonFiles+templateFileName)[0]
		parsed_content = renderer.parse(template_source)
		variables = meta.find_undeclared_variables(parsed_content)
		unusedVariables = [ var for var in variables if var not in d ]
		if unusedVariables and Config.options.verbosity>0:
			print( Fore.GREEN + "In the template '" + templateFileName + "' the following variables are unused :" + ",".join(unusedVariables) + Fore.RESET + Style.NORMAL)



	def checkDifferences(self, data):
		"""compare the current session with the previous one (to check if something has changed and if we need to build it or not)"""
		self.remainsUnchanged = not set( (key,md5(val.encode('utf-8')).hexdigest()) for key,val in self.dict.items() ) - set(data.items())
