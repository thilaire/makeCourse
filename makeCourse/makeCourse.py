# -*- coding: utf-8 -*-


"""
MakeCourse
"""
import os
from tempfile import mkdtemp
from colorama import Fore, Style
from bs4 import BeautifulSoup, Comment, NavigableString
import codecs
from pickle import dump, load
from hashlib import md5

from .osUtils import runCommand, fileAlmostExists, createDirectory, cd, splitToComma
from .mkcException import mkcException
from .Session import Session
from .config import Config

print( Fore.RED+"---- MakeCourse v0.3 ----"+Fore.RESET)



def containsTextOnly( tag):
	return (not tag.attrs) and tag.string

def notContainsTextOnly( tag):
	return not containsTextOnly( tag)



def importFiles( bfs, importScheme ):
	"""Import the files in a beautifulSoup object (tag)"""

	# import the external files
	for tag in bfs( lambda x: x.has_attr('import'), recursive=False):
		imported = []
		for fn in splitToComma( tag["import"] ):
			# get the filename (from the importScheme dictionary)
			toImport = fn.strip().split(":")
			d = {"#"+str(i+1):n for i,n in enumerate(toImport[:-1])}
			d.update(tag.attrs)
			try:
				path = importScheme.get(tag.name,'').format( **d )
			except:
				raise mkcException( "The import path '"+fn+"' is not valid (do not correspond to the scheme '"+importScheme.get(tag.name,'')+"'!)" )
			fileNameExt = path + toImport[-1]
			fileNameExt = fileNameExt.split(".")
			fileName = fileNameExt[0] if len(fileNameExt)==1 else ".".join(fileNameExt[:-1])	# everything except the extension of the file, if there is an extension
			# check if the file exist
			if len(fileNameExt)==1:
				fileName = fileAlmostExists(fileName, 'xml') or fileAlmostExists(fileName)
			else:
				fileName = fileAlmostExists(fileName, fileNameExt[-1])
			if not fileName:
				if tag in importScheme:
					raise mkcException( "The file "+path + toImport[-1] + ".xml"+" cannot be imported, it does not exist!" )
				else:
					raise mkcException( "The file "+path + toImport[-1] + ".xml"+" cannot be imported, probably because there is no specified path for the importation of tag <"+tag.name+">")
			# open the file, insert it in place
			if Config.options.verbosity>0:
				print( Fore.MAGENTA+"  Import file "+ fileName)
			if fileName.split('.')[-1] == 'xml':
				im = BeautifulSoup(codecs.open(fileName, encoding=tag.attrs.get('encoding','utf-8')),features="xml")
				if im.contents:

#TODO: ne marche pas pour un commentaire dans un fichier xml importé...
					
					if im.contents[0].name == tag.name and len(splitToComma( tag["import"] ))==1 :
						im.contents[0].attrs.update(tag.attrs)
						tag.replace_with( im.contents[0] )						
					else:
						tag.append(im.contents[0])
				else:
					raise mkcException( 'The file '+fileNameExt+' is not valid !')
			else:
				tag.append( codecs.open(fileName, encoding=tag.attrs.get('encoding','utf-8')).read() )

			imported.append(fileName)
		tag["imported"] = ', '.join( "'"+i+"'" for i in imported)
		del tag["import"]

	# recursive import
	for tag in bfs( notContainsTextOnly, recursive=False):
		importFiles( tag, importScheme)


def makeCourse( xmlFile, genPath, importPaths, commonFiles):
	"""Parse the course xml-file and treate the command line...
	Parameters:
		- xmlFile: name of the XML file containing the description of the course
		- genPath: path where to put the produced documents
		- importPaths: schemes to know where to import stuff (dictionnary tags -> path scheme)
		- commonFiles: schemes to know where to find the commonFiles (dictionary session -> path)
	"""
	try:

		# parse the command line
		Config.add_option('--verbose', help='Set verbosity to maximum', dest='verbosity', default=0, action='store_const', const=2)
		Config.add_option('-v','--verbosity', help='Set the verbosity level (0: quiet, 1: display the command lines, 2: display command lines and their outputs', dest='verbosity', default=0, type=int)
		Config.add_option('-d', '--debug', help='Create the files in the debug/ folder, instead of in a temporary one', dest='debug', action='store_true', default=False)
		Config.add_option('-f', '--force', help='Force the generation of the documents, even if nothing changes from last run', dest='force', action='store_true', default=False)
		Config.parse()
		args = Config.args
		options = Config.options

		# clean the debug directory in debug mode
		basePath = os.path.abspath('.')+'/'			# base path (from where the script is run, because the path are relative)
		if options.debug:
			if os.path.exists('debug/'):
				runCommand(['rm','-rf','debug/'])

		# open and parse the course file
		with codecs.open(xmlFile, encoding='utf-8') as f:
			bs = BeautifulSoup(f, features="xml")

		importFiles( bs.contents[0], importPaths)

		# get the list of sessions we can build (with a 'make' method)
		buildableSessions = { x.__name__:x for x in Session.__subclasses__() if 'make' in x.__dict__ }

		# build the list of Sessions to build
		sessionsToBuild = []
		for name,session in buildableSessions.items():
			sessionsToBuild.extend( session(tag, commonFiles) for tag in bs(name) )


		# if possible, load the previous xml file, and look for the differences
		try:
			with open(".makeCourse.data", "rb") as f:
				data = load( f )
				for s in sessionsToBuild:
					if s.name in data:
						s.checkDifferences( data[s.name] )
		except IOError:
			pass


		runCommand(['echo', '$PATH'])



		# build every argument in the command line arguments
		somethingHasBeDone = False
		for s in sessionsToBuild:
			if (not args) or ("all" in args) or (s.name in args) or (s.type in args):
				
				cd( basePath)
				
				# check if something has to be done
				if s.shouldBeMake(basePath+'/'+genPath) or options.force:
					somethingHasBeDone = True

					#Make one build (TP, course, etc.)
					print ( Fore.BLUE+"*) Make "+Style.BRIGHT+s.name+Fore.RESET+Style.NORMAL)

					# make temp directory and copy all the file in resources dir
					if options.debug:
						tmp = "debug/"+s.name+'/'
						createDirectory(tmp)
					else:
						tmp = mkdtemp()

					s.prepareResources(tmp )
					cd( tmp)

					# call the custom function associated with the type, to produce the documents
					s.make(options)

					# then move the files in the right place
					for f in s.files():
						createDirectory( basePath+'/'+genPath.format( **s.dict ) )
						newFile = basePath+'/'+genPath.format( **s.dict )+f
						if not os.path.exists(f):
							print( Fore.YELLOW+'The file '+f+' has not been created by '+s.type+' function !'+Fore.RESET)
						runCommand( ['cp', f, newFile])

					# del the temporary directory or clean debug directory
					if not options.debug:
						runCommand( ['rm', '-rf', tmp])
				else:
					if options.verbosity>0:
						print( Fore.BLUE + "*) Nothing changed for "+Style.BRIGHT+s.name+Style.NORMAL+", skipped"+Fore.RESET)



		if not somethingHasBeDone:
			print( Fore.BLUE + "Nothing has changed, nothing to do, nothing has been done..." + Fore.RESET)


		# save the data file
		data = {L.name: {key:md5(val.encode('utf-8')).hexdigest() for key,val in L.dict.items()} for L in sessionsToBuild }
		cd( basePath)
		with open('.makeCourse.data', 'wb') as f:
			dump( data, f)







	except mkcException as err:
		print( err )
