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

import pypandoc

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


def convertStringTag( tag, convertTo):
	"""convert a text-only tag to a format (latex, markdown, etc.)
	according to its format (given by its attribute 'format')"""
	if convertTo and ('format' in tag.attrs) and convertTo!=tag['format']:
		return pypandoc.convert(tag.string, convertTo, format = tag['format'])
	else:
		return tag.string
	
def convertString( string, convertFrom, convertTo):
	if convertFrom and convertTo and convertFrom!=convertTo:
		return pypandoc.convert( string, convertTo, format=convertFrom)
	else:
		return string

class Session(object):

	number = 0		# number of objects created
	format = ''		# intern format (LaTex, markdown, etc.)
	
	
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
				self.dict = dict( {tag.name:convertStringTag(tag,self.format) for tag in p( containsTextOnly, recursive=False) }, **self.dict )

		self.dict.update( tag.attrs)
		self.dict.update( {tag.name:convertStringTag(tag,self.format) for tag in self.tag( containsTextOnly, recursive=False) } )


		self.dict [ 'type' ] = self.type
		self.name = tag.get('name') or self.dict.get('name') or self.type+str(type(self).number) 		# name of the Session (usually type+number)
		self.dict[ 'name' ] = self.name
		self.remainsUnchanged = False

		#contents
		self.dict[ 'Content' ] = '\n'.join( [convertString(l, convertFrom=self.tag.attrs.get('format',''), convertTo=self.format) for l in self.tag.contents if isinstance(l,NavigableString) and not isinstance(l,Comment)] )
		


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


	def getStringFromTemplate(self, templateFileName, dictionary={}, encoding='utf-8'):
		"""Read the template file and fill it with the dictionnary (and the content of the session, of course)
		and returns the result
		"""
		#open the template file
		template = renderer.get_template( self.commonFiles+templateFileName, encoding)
		# dictionary for the template file
		d = dict( dictionary, **self.dict)		# http://stackoverflow.com/questions/1781571/how-to-concatenate-two-dictionaries-to-create-a-new-one-in-python
		d["Filename"] = self.commonFiles+templateFileName
		now = datetime.datetime.now()
		d['Date'] = now.strftime('%d/%m/%Y - %H:%M')
		
		# render the template
		t=template.render( d )

		# get the list of unused variables
		# cf http://stackoverflow.com/questions/8260490/how-to-get-list-of-all-variables-in-jinja-2-templates
		parsed_content = renderer.parse(template)
		variables = meta.find_undeclared_variables(parsed_content)
		unusedVariables = [ var for var in variables if var not in d ]
		if unusedVariables and Config.options.verbosity>0:
			print( Fore.GREEN + "In the template '" + templateFileName + "' the following variables are unused :" + ",".join(unusedVariables) + Fore.RESET + Style.NORMAL)

		
		return t
	

	def writeFileFromTemplate(self, templateFileName, fileName, dictionary={}, encoding='utf-8'):
		"""Read the template file, and fill it with the dictionnary (and the content of the session, of course)
		and save it in the temporary directory
		"""
		# fill the template
		t = self.getStringFromTemplate(templateFileName, dictionary, encoding)
		#create the new file
		resultFile = io.open( fileName, "w", encoding=encoding)
		resultFile.write( t )
		resultFile.close()


	def checkDifferences(self, data):
		"""compare the current session with the previous one (to check if something has changed and if we need to build it or not)"""
		self.remainsUnchanged = not set( (key,md5(val.encode('utf-8')).hexdigest()) for key,val in self.dict.items() ) - set(data.items())
