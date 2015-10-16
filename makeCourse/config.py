import optparse


class Config:

	options = None						# options from the command line
	args = None
	_parser = optparse.OptionParser()	# option parser
	importPaths = {}					# importPaths: schemes to know where to import stuff (dictionnary tag name -> path scheme)
	commonFiles = {}					# commonFiles: schemes to know where to find the commonFiles (dictionary session name -> path)
	allSessions = {}
	rendererContent = False				# tells if we should renderer the Content or not 
	
	@staticmethod
	def add_option(*opt1,**opt2):
		Config._parser.add_option(*opt1,**opt2)


	@staticmethod
	def parse():
		(Config.options,Config.args) = Config._parser.parse_args()

