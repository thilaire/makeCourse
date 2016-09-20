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
from .osUtils import runCommand, getPathTime, splitToComma, fileAlmostExists
from .config import Config

from .mkcException import mkcException
from bs4 import BeautifulSoup
import codecs

from .StrLang import StrLang


def createTagSession( tag, father):
	"""take a beautifulsoup tag and return a Tag object or a Session object, according to the name"""
	return Config.allSessions.get( tag.name, Tag)( tag, father)



# jinja renderer (change the default delimiters used by Jinja such that it won't pick up brackets attached to LaTeX macros.)
# cfhttp://tex.stackexchange.com/questions/40720/latex-in-industry
renderer = jinja2.Environment(
                        block_start_string = '{%%',
                        block_end_string = '%%}',
                        comment_start_string='{%<',
                        comment_end_string='>%}',
                        variable_start_string = '{{<',
                        variable_end_string = '>}}',
                        loader = jinja2.FileSystemLoader( os.path.abspath('.') )
                )


def containsTextOnly( tag):
	return (not tag.attrs) and tag.string and not tag.find_all()

def doesNotContainsTextOnly( tag):
	return not containsTextOnly(tag) or tag.name in Config.allSessions



class Tag(object):
	"""XML tag
	- tag (beautifulsoup tag)
	- dict (dictionary of attributes and stringOnly sons)
	   attr -> string (StrLang)
	"""

	def __init__(self, tag, father):
		
		self.tag = tag # store the beautifulSoup tag
		self.father = father
		
		# import the files (extend the BeautifulSoup tag)
		self.importFiles()
		
		# determine the language (LaTeX, Markdown, etc.)
		self.lang = father.lang if father else None
		if "lang" in tag.attrs:
			self.lang = tag.attrs["lang"]
		
		# build the dictionary 
		self.dict = dict(father.dict) if father else {}	# from the father
		self.dict.update( { attr: StrLang(val, self.lang) for attr,val in tag.attrs.items() } )	# from attributes
		d = {}	# and from string-only children tags (that are not a session)
		for t in tag( containsTextOnly, recursive=False):
			if t.name not in Config.allSessions:
				d[t.name] = StrLang(t.string, t.attrs.get("lang",self.lang))
		self.dict.update(d)

		# recursive built
		self.children = [ createTagSession(t, self) for t in self.tag(doesNotContainsTextOnly,recursive=False) ]	
			

		
	def importFiles(self):
		"""import the external files, according to the 'import' attribute"""
		
		if self.tag.has_attr('import'):
			imported = []
			# iterate over each filename
			for fn in splitToComma( self.tag["import"] ):
				# get the filename (from the importPaths dictionary)
				toImport = fn.strip().split(":")
				d = {"#"+str(i+1):n for i,n in enumerate(toImport[:-1])}
#TODO: changer self.tag.attrs par self.dict				
				d.update(self.tag.attrs)
				try:
					path = Config.importPaths.get( self.tag.name, '' ).format( **d )
				except:
					raise mkcException( "The import path '"+fn+"' is not valid (do not correspond to the scheme '"+Config.importPaths.get(self.tag.name,'')+"' !)" )
				fileNameExt = path + toImport[-1]
				fileNameExt = fileNameExt.split(".")
				fileName = fileNameExt[0] if len(fileNameExt)==1 else ".".join(fileNameExt[:-1])	# everything except the extension of the file, if there is an extension
				# check if the file exist
				if len(fileNameExt)==1:
					fileName = fileAlmostExists(fileName, 'xml') or fileAlmostExists(fileName)
				else:
					fileName = fileAlmostExists(fileName, fileNameExt[-1])
				if not fileName:
					if self.tag in Config.importPaths:
						raise mkcException( "The file " + path + toImport[-1] + ".xml"+" cannot be imported, it does not exist (or several paths exist)!" )
					else:
						raise mkcException( "The file " + path + toImport[-1] + ".xml"+" cannot be imported, probably because there is no specified path for the importation of tag <"+self.tag.name+"> or the file "+path + toImport[-1] + ".xml doesn't exist")
				# open the file, insert it in place
				if Config.options.verbosity>0:
					print( Fore.MAGENTA+"  Import file "+ fileName)
				if fileName.split('.')[-1] == 'xml':
#TODO: changer self.tag.attrs par self.dict					
					im = BeautifulSoup(codecs.open(fileName, encoding=self.tag.attrs.get('encoding','utf-8')),features="xml")
					if im.contents:
						if im.contents[0].name == self.tag.name and len(splitToComma( self.tag["import"] ))==1 :
							self.tag.attrs.update( im.contents[0].attrs )
							#self.tag.replace_with( im.contents[0] )		#-> doesn't work, for an unknown reason (it used to work before...)
							self.tag.append(im.contents[0])
							self.tag(self.tag.name)[0].unwrap()
					
						else:
							for i in range(len(im.contents)):
								self.tag.append(im.contents[0])
					else:
						raise mkcException( 'The file '+fileName+' is not valid !')
				else:
					self.tag.append( codecs.open(fileName, encoding=self.tag.attrs.get('encoding','utf-8')).read() )
	
				imported.append(fileName)
				
			self.tag["imported"] = ', '.join( "'"+i+"'" for i in imported)
			del self.tag["import"]
	

	

class Session(Tag):

	number = 0		# number of objects created (per session type)
	sessionsToBuild = []		# list of the sessions object to build
	
	def __init__(self, tag, father):
		"""
		- tag (beautifulSoup object) to build the session
		- dictionary of commonFiles
		"""
		
		super().__init__(tag, father)
		
		type(self).number += 1						# add one session
		self.type = type(self).__name__				# name of the type of Session
		
		# define the common files to be included/copied
		if self.type in Config.commonFiles:
			self.commonFiles = Config.commonFiles[ self.type ]						
		elif 'make' not in type(self).__dict__:	# class contains a 'make' method
			self.commonFiles = ''
		else:
			raise mkcException( "There is no commonFiles for the session "+self.type+ "!" )


		self.dict [ 'type' ] = self.type
		self.name =  tag.get('name') or self.dict.get('name') or self.type+str(type(self).number)		# name of the Session (usually type+number)
		self.dict[ 'name' ] = self.name
		self.remainsUnchanged = False

		#contents
		self.dict[ 'Content' ] = StrLang( '\n'.join( l for l in self.tag.contents if isinstance(l,NavigableString) and not isinstance(l,Comment) ), lang=self.lang )

		# check if the Session has to be built or not
		if 'make' in type(self).__dict__:
			Session.sessionsToBuild.append(self)

	def files(self, options):
		"""returns the files that are produced when making the session (none if not specified)"""
		return []
	
		


	def shouldBeMake(self, scheme, options):
		"""determine if the unit should be make
		(the documents of the units should be produced)
		(if the previously produced files are older than the files necessary to build the unit, then we should make the unit
		"""
		if self.remainsUnchanged:
			# get the time of the oldest produced file (if the file exist)
			oldestTimeProducedFile = time.time()
			for f in self.files(options):
				target = scheme.format( **self.dict ) + f
				targetTime = os.path.getmtime(target) if os.path.exists(target) else 0
				if oldestTimeProducedFile>targetTime:
					oldestTimeProducedFile = targetTime
			# get the time of all the possible files
			importedFiles = splitToComma( self.tag.get("imported","") )
			pathTimes = [ getPathTime(os.path.dirname(p.strip())) for p in importedFiles ]
			if pathTimes and self.tag["imported"]:
				newestTimeParts = max( pathTimes )
			else:
				newestTimeParts = 0

			return newestTimeParts > oldestTimeProducedFile
		else:
			return True


	def prepareResources(self, dest):
		"""Prepare (copy) the resources (commonFiles) of a session into the dest folder (temporary or debug) """
		runCommand( ['cp', self.commonFiles+'*', dest])
		done = {}
		for p in splitToComma( self.tag.get("imported",'') ):
			pPath = '/'.join(p.strip().split('/')[0:-1])
			if pPath not in done:
				runCommand( ['cp', '-R', pPath+"/*", dest])
				done[ pPath ]=True


	def getStringFromTemplate(self, templateFileName, dictionary=None, lang=None, encoding='utf-8' ):
		"""Read the template file and fill it with the dictionnary (and the content of the session, that is also templated, of course)
		and returns the result
		"""
		
		# dictionary for the template file
		if dictionary is None:
			dictionary = { }
		d = dict( self.dict, **dictionary )		# http://stackoverflow.com/questions/1781571/how-to-concatenate-two-dictionaries-to-create-a-new-one-in-python
		d["Filename"] = self.commonFiles+templateFileName
		now = datetime.datetime.now()
		d['Date'] = now.strftime('%d/%m/%Y - %H:%M')
		
		# translate the dictionary
		for k,v in d.items():
			if isinstance(v,StrLang):
				d[k] = v.convertTo(lang)

		# template the Content
		if Config.rendererContent:
			template = renderer.from_string(d["Content"])
			d["Content"] = template.render(d)

		
		#open the template file and render it
		template = renderer.get_template( self.commonFiles+templateFileName, encoding)
		t=template.render( d )

		# get the list of unused variables
		# cf http://stackoverflow.com/questions/8260490/how-to-get-list-of-all-variables-in-jinja-2-templates
		parsed_content = renderer.parse(template)
		variables = meta.find_undeclared_variables(parsed_content)
		unusedVariables = [ var for var in variables if var not in d ]
		if unusedVariables and Config.options.verbosity>0:
			print( Fore.GREEN + "In the template '" + templateFileName + "' the following variables are unused :" + ",".join(unusedVariables) + Fore.RESET + Style.NORMAL)

		
		return t
	

	def writeFileFromTemplate(self, templateFileName, fileName, dictionary=None, lang=None, encoding='utf-8' ):
		"""Read the template file, and fill it with the dictionnary (and the content of the session, of course)
		and save it in the temporary directory
		"""
		# fill the template
		if dictionary is None:
			dictionary = { }
		t = self.getStringFromTemplate(templateFileName, dictionary, lang, encoding)
		#create the new file
		resultFile = io.open( fileName, "w", encoding=encoding)
		resultFile.write( t )
		resultFile.close()


	def checkDifferences(self, data):
		"""compare the current session with the previous one (to check if something has changed and if we need to build it or not)"""
		self.remainsUnchanged = not set( (key,md5(str(val).encode('utf-8')).hexdigest()) for key,val in self.dict.items() ) - set(data.items())
		
		
	def iterall(self, tagName):
		"""return a generator on the children with a tag 'tagName'"""
		return (t for t in self.children if t.tag.name==tagName)
