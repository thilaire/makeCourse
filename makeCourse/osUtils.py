from glob import glob
from subprocess import Popen, PIPE, call, list2cmdline
from colorama import Fore
import os
from collections import deque
from .config import Config
import re
import unicodedata
import platform


regex_comma = re.compile(r'''((?:[^,"']|"[^"]*"|'[^']*')+)''')

#http://stackoverflow.com/questions/5581857/git-and-the-umlaut-problem-on-mac-os-x
if platform.system()=='Darwin':
	unicode_normalization = 'NFD'
else:
	unicode_normalization ='NFC'	


def splitToComma( text):
	# split to comma but ignore comma in quoted strings
	#http://stackoverflow.com/questions/2785755/how-to-split-but-ignore-separators-in-quoted-strings-in-python
	return [ st.strip(' \'\"') for st in regex_comma.split(text)[1::2] ]


def runCommand( cmd, times=1):
	"""run shell command, several times
	(and manage the errors)"""
	last10 = deque(10*[''], 10)# last 10 lines
	if Config.options.verbosity>0:
		print  (Fore.MAGENTA+'>'+list2cmdline(cmd)+Fore.RESET)
	for i in range(times):
		proc = Popen( list2cmdline(cmd), stdout=PIPE, shell=True)
		display = False
		line = 'toto'
		while line:
			line = proc.stdout.readline().decode("utf-8")
			last10.pop()
			last10.appendleft(line)
			# start to display when output starts with '!' (for LaTeX errors)
			display = display or line.startswith('!')
			if display or Config.options.verbosity>1:
				if len(last10)>1:
					print( ''.join(last10).rstrip() )
					last10.clear()
					last10.appendleft(line)
				else:
					print( line.rstrip())


def cd( path):
	"""Change directory"""
	if Config.options.verbosity>0:
		print( Fore.MAGENTA+ '>cd '+path+Fore.RESET)
	os.chdir(path)


def createDirectory( dir):
	"""Do the necessary to create directory (or do nothing if it exists)
	works with xxx/yyy/zzz even if xxx or xxx/yyy do not exist"""
	ldir = dir.split('/')
	d = ''
	for sd in ldir:
		d = d + sd + '/'
		if not os.path.exists(d):
			if Config.options.verbosity>0:
				print( Fore.MAGENTA+">mkdir "+d+Fore.RESET)
			os.mkdir(d)

def getPathTime(dir):
	"""Get the latest time of all the files of a directory (and subdirectory)"""
	pathTimes = [ os.path.getmtime( os.path.join(root,f) ) for root, subFolders, files in os.walk(dir) for f in files ]
	return pathTimes and max( pathTimes ) or 0


def fileAlmostExists(fileNamePath, extension='*'):
	"""Check if a file exists (from it path and filename)
	For each subfolder of fileNamePath, we check if the folder really exists, or if there is only one folder with a name approaching the subfolder (begin or end with)
	Return the true validated fileName or None if the file doesn't exist """

	partial = []		# list of the partial path ("/".join(partial) gives the full path)
	for d in fileNamePath.split('/'):
		pr = '.' + extension if d==fileNamePath.split('/')[-1] else '' # get the prefix only for the last part (filename only, not path)
		# check if d exists, if a (unique) folder starting with d exists, a (unique) folder ending with d, or a (unique) folder containing d (in that order)
		for p in ( d, d+'*', '*'+d, '*'+d+'*' ):

			# need to denormalize unicode string to be able to search for filename with accents
			# see http://nedbatchelder.com/blog/201106/filenames_with_accents.html
			# and http://stackoverflow.com/questions/14185114/pythons-glob-module-and-unix-find-command-dont-recognize-non-ascii
			denorm = unicodedata.normalize(unicode_normalization, "/".join(partial+[p])+pr )
			res = glob( denorm )
			if len(res)==1:
				partial.append( res[0].split("/")[-1] )		# append the last part of the path
				break
		else:
			return None

	return "/".join(partial)
