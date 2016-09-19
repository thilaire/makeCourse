# -*- coding: utf-8 -*-


"""
MakeCourse
"""
import os
from tempfile import mkdtemp
from colorama import Fore, Style
from bs4 import BeautifulSoup
import codecs
from pickle import dump, load
from hashlib import md5

from .osUtils import runCommand, createDirectory, cd
from .mkcException import mkcException
from .Session import Session, createTagSession

from .config import Config
from os.path import split


print( Fore.RED+"---- MakeCourse v0.4 ----"+Fore.RESET)




def makeCourse( xmlFile, genPath, importPaths, commonFiles, rendererContent=True):
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
		Config.add_option('-q', '--quick', help='Quick pdf generation (do not compile twice the latex, do not produce handout, etc.)', dest='quick', action='store_true', default=False)
		Config.add_option('--wordpress', help='Publish to wordpress', dest='wordpress', default=False, action='store_true')
		Config.parse()
		args = Config.args
		options = Config.options
		Config.importPaths = importPaths 
		Config.commonFiles = commonFiles
		Config.allSessions = { x.__name__:x for x in Session.__subclasses__()}	# list of the created session classes
		Config.rendererContent = rendererContent
		
		# clean the debug directory in debug mode
		basePath = os.path.abspath('.')+'/'			# base path (from where the script is run, because the path are relative)
		if options.debug:
			if os.path.exists('debug/'):
				runCommand(['rm','-rf','debug/'])

		# open and parse the course file
		with codecs.open(xmlFile, encoding='utf-8') as f:
			bs = BeautifulSoup(f, features="xml")


		# build the recursively the sessions
		top = createTagSession( bs, father=None )		# bs.contents[0]
		sessionsToBuild = Session.sessionsToBuild		# get the list of the sessions object
		

		"""
		importFiles( bs.contents[0], importPaths)

		# get the list of sessions we can build (with a 'make' method)
		buildableSessions = { x.__name__:x for x in Session.__subclasses__() if 'make' in x.__dict__ }

		#This set the PATH for PyDev only...
		os.environ['PATH'] = os.environ['PATH']+':'+os.getenv('PATH')


		# build the list of Sessions to build
		sessionsToBuild = []
		for name,session in buildableSessions.items():
			sessionsToBuild.extend( session(tag, commonFiles) for tag in bs(name) )
		"""
		
		

		# if possible, load the previous xml file, and look for the differences
		dirName,baseName = split(xmlFile) 
		try:
			with open(dirName+"/."+baseName+".makeCourse", "rb") as f:
				data = load( f )
				for s in sessionsToBuild:
					if s.name in data:
						s.checkDifferences( data[s.name] )
		except IOError:
			pass


		# build every argument in the command line arguments
		somethingHasBeDone = False
		for s in sessionsToBuild:
			if (not args) or ("all" in args) or (s.name in args) or (s.type in args):
				
				cd( basePath)
				
				# check if something has to be done
				if s.shouldBeMake(basePath+'/'+genPath, options) or options.force:
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
					for f in s.files(options):
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
			print( Fore.BLUE + "Nothing has changed, nothing to do, so nothing has been done..." + Fore.RESET)


		# save the data file
		data = {L.name: {key:md5(str(val).encode('utf-8')).hexdigest() for key,val in L.dict.items()} for L in sessionsToBuild }
		cd( basePath)
		with open(dirName+"/."+baseName+".makeCourse", 'wb') as f:
			dump( data, f)







	except mkcException as err:
		print( err )
