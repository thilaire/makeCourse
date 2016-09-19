"""
	Upload data to Wordpress website
	using API JSON (and API JSON AUTH)
	
	https://wordpress.org/plugins/json-api
	https://wordpress.org/plugins/json-api-auth/
	
"""

import requests
from colorama import Fore
from .config import Config
from getpass import getpass
from .mkcException import mkcException


def getRequest(url, **params):
	"""get the request (with requests package) and pretty-print stuff for verbose cases"""
	# prepare request
	req = requests.Request('GET', url, params=params)
	prepared = req.prepare()
	# pretty-print url (if needed)
	if Config.options.verbosity>0:
		print( Fore.GREEN + '> GET ' + prepared.url + Fore.RESET, end='')
	
	# get request
	s = requests.Session()
	r = s.send(prepared)
	
	# pretty-print status (if needed)
	if r.status_code == requests.codes.ok and r.json()['status']=='ok':
		if Config.options.verbosity>0:
				print( '  (status=' + Fore.GREEN + 'ok' + Fore.RESET + ')')
		if Config.options.verbosity>1:
			print( Fore.MAGENTA+ '>>> ' + str(r.json()) + Fore.RESET )
	elif r.status_code != requests.codes.ok:
		if Config.options.verbosity>0:
			print( '  (status=' + Fore.RED + 'ko' + Fore.RESET + ')')
		if Config.options.verbosity>1:
			print( Fore.MAGENTA + '>>> ' + r.reason + ': ' + r.text + Fore.RESET)
		raise mkcException( 'Get request impossible\nRequest='+r.url+'\nReason='+r.reason + ': ' + r.text)
	else:
		if Config.options.verbosity>0:
			print( '  (status=' + Fore.RED + 'ko' + Fore.RESET + ')')
		if Config.options.verbosity>1:
			print( Fore.MAGENTA + '>>> ' + str(r.json()) + Fore.RESET)
		raise mkcException( 'Get request impossible\nRequest='+r.url+'\nAnswer='+str(r.json()))
			
		
	return r
	

class WP:
	
	def __init__(self, url, user, password=None):
		"""store id to connect to wordpress site
		if password=None, it will be asked for the 1st request"""
		self.url = url
		self.user = user
		self.password = password
		self.cookie = None

		
		if password:
			self.getCookie()
	
	
	def getCookie(self):
		"""retrieve cookie for authentification to Wordpress site (via API JSON Auth)"""
		r = getRequest( self.url, controller='auth', method='generate_auth_cookie', json='get_nonce')
		nonce = r.json()['nonce']
		r = getRequest( self.url, json='auth.generate_auth_cookie', nonce=nonce, username=self.user, password=self.password) 
		self.cookie = r.json()['cookie']

	
	def getWPRequest(self, controller, method, **params):
		"""Get request
		ask the user for the password for the 1st request if it were not given to the constructor"""
		# get the cookie if the authentification is not yet been done
		if not self.cookie:
			print("Enter the password to log in to "+self.url+' (user='+self.user+'): ')
			self.password = getpass()
			self.getCookie()
		# get nonce
		r = getRequest( self.url, controller=controller, method=method, json='get_nonce', cookie=self.cookie)
		nonce = r.json()['nonce']
		# proceed request
		params.update({'json':method,'nonce':nonce,'cookie':self.cookie} )
		r = getRequest( self.url, **params) 
		return r.json()
		
		
	def createPost(self,title, content, status="publish", categories="", tag=""):
		"""
			status: sets the post status ("draft" or "publish"), default is "draft"
			title: the post title
			content: the post content
			author: the post's author (login name), default is the current logged in user
		"""
		return self.getWPRequest( 'posts', 'create_post', title=title, content=content, status=status, categories=categories, tag=tag)


	def updatePost(self, id, title, content, status="publish", categories="", tag=""):
		"""
			id: id of the post to be updated
			status: sets the post status ("draft" or "publish"), default is "draft"
			title: the post title
			content: the post content
			author: the post's author (login name), default is the current logged in user
		"""
		print("'"+content+"'")
		return self.getWPRequest( 'posts', 'update_post', id=id, title=title, content="'"+content+"'", status=status, categories=categories, tag=tag)


	def getId(self, title, category):
		
		r = self.getWPRequest('core','get_posts', category_name=category)
		l = [ p['id'] for p in r['posts'] if p['title']==title ]
		
		if len(l)==1:
			return l[0]
		elif len(l)==0:
			return 0
		else:
			raise mkcException("Several posts exists with title="+title+" and category="+category)
		
		
	def createUpdatePost(self, title, content, category, status="publish", tag=""):
		
		# check if the post already exists
		id = self.getId( title, category)
		if id==0:
			self.createPost(title, content, status, category, tag)
		else:
			self.updatePost(id, title, content, status, category, tag)
		