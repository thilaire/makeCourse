import optparse

class Config:

	options = None						# options from the command line
	args = None
	_parser = optparse.OptionParser()	# option parser

	@staticmethod
	def add_option(*opt1,**opt2):
		Config._parser.add_option(*opt1,**opt2)


	@staticmethod
	def parse():
		(Config.options,Config.args) = Config._parser.parse_args()
