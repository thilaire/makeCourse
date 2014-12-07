from colorama import Fore

class mkcException(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		
		return Fore.RED + self.msg + Fore.RESET
