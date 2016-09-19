from makeCourse.Session import Session
from makeCourse.osUtils import runCommand
from makeCourse.config import Config
from makeCourse.mkcException import mkcException


class CM(Session):
	"""Define a CM ('cours magistral')"""
	
	def make(self, options):
		if not options.quick:
			# build and compile (handout)
			print( " - build handout")
			self.writeFileFromTemplate( 'CM.tex', self.name+'-handout.tex', {'documentclass' :  '\documentclass[handout]{beamer}'}, lang='latex' )
			runCommand( ['pdflatex', self.name+'-handout.tex'],2 )
			# printable bersion
			print( " - build printable version")
			runCommand(  ['pdfnup', '-q', '--nup', '2x2', '--suffix', "'2x2'", self.name+'-handout.pdf'] )
		# build and compile (slides)
		print( " - build slides")
		self.writeFileFromTemplate( 'CM.tex', self.name+'.tex', {'documentclass' :  '\documentclass{beamer}'}, lang='latex' )
		runCommand( ["pdflatex", self.name+".tex"], 1 if options.quick else 2  )
		if not options.quick:

			# build widescreen version
			print( " - build widescreen slides")
			self.writeFileFromTemplate( 'CM-screencast.tex', self.name+'-screencast.tex', lang='latex' )
			runCommand( ["pdflatex", self.name+"-screencast.tex"], 2 )
		

	def files(self, options):
		if options.quick:
			return [self.name+".pdf"]
		else:
			return [self.name+".pdf", self.name+'-handout.pdf', self.name+'-handout-2x2.pdf', self.name+'-screencast.pdf' ]



class TP(Session):
	"""Définit une séance de TP"""

	def make( self, options):
		# met à jour le fichier sty (avec année, etc.)
		self.writeFileFromTemplate( 'tdtme.sty', 'tdtme.sty')
		# construit le LaTeX des exercices
		Content = '\n'.join( e.LaTeX() for e in self.iterall('Exercice') ) +  self.dict["Content"].convertTo(lang='latex')		# construit et compile
		print( " - build student version")
		self.writeFileFromTemplate( 'TP.tex', self.name+'-eleves.tex', {'Enseignants' :  '', 'Content':Content}, lang='latex')
		runCommand( ["pdflatex", self.name+"-eleves.tex"], 2 )
		# construit et compile (version enseignant)
		print( " - build teacher version")
		self.writeFileFromTemplate( 'TP.tex', self.name+'-enseignants.tex', {'Enseignants' :  '[enseignants]', 'Content':Content}, lang='latex')
		runCommand( ["pdflatex", self.name+"-enseignants.tex"], 2 )
		# export to wordpress
		if options.wordpress:
			print( " - export to wordpress")
			content = self.getStringFromTemplate('TP-wp.txt', lang='html', encoding='utf-8')
			Config.WP.createUpdatePost(title=self.name, content=content, category=Config.WPcategory)
		# export files to ssh
		if options.shared:
			print(" - export files to " + Config.sharedOpt["host"])
			if not self.dict['sharedPath']:
				raise mkcException("The path <sharedPath> should exist to export the files to " + Config.sharedOpt["host"])
			# remote mkdir
			runCommand(['ssh', "{user}@{host}".format(**Config.sharedOpt), 'mkdir', '-p', str(self.dict['sharedPath']) ])
			if 'shared' in self.dict:
				# copy each file
				for f in str(self.dict['shared']).split(','):
					runCommand(['scp', f.strip(), "{user}@{host}:{path}".format( path=str(self.dict['sharedPath']), **Config.sharedOpt ) ])
			# copy the pdf file
			runCommand(['scp', self.name+"-eleves.pdf", "{user}@{host}:{path}".format( path=str(self.dict['sharedPath']), **Config.sharedOpt ) ])
			
	def files(self, options):
		listShared = []
		if 'shared' in self.dict:
			listShared = str(self.dict['shared']).split(',') 
		return [ self.name+"-eleves.pdf", self.name+"-enseignants.pdf"] + listShared


		
class TD(Session):
	"""Définit une séance de TD"""
	def make( self, options):
		# met à jour le fichier sty (avec année, etc.)
		self.writeFileFromTemplate( 'tdtme.sty', 'tdtme.sty')
		# construit le LaTeX des exercices
		Content = '\n'.join( e.LaTeX() for e in self.iterall('Exercice') ) +  self.dict["Content"].convertTo(lang='latex')
		# construit et compile
		print( " - build student version")
		self.writeFileFromTemplate( 'TD.tex', self.name+'-eleves.tex', {'Enseignants' :  '', 'Content':Content}, lang='latex')
		runCommand( ["pdflatex", self.name+"-eleves.tex"], 2 )
		# construit et compile (version enseignant)
		print( " - build teacher version")
		self.writeFileFromTemplate( 'TD.tex', self.name+'-enseignants.tex', {'Enseignants' :  '[enseignants]', 'Content':Content}, lang='latex')
		runCommand( ["pdflatex", self.name+"-enseignants.tex"], 2 )

		# affiche le SPIP correspondant
		strSpip = '\n'.join( e.Spip() for e in self.iterall('Exercice') )
		
		
	def files(self, options):
		return [ self.name+"-eleves.pdf", self.name+"-enseignants.pdf"]


class projet(Session):
	"""Définit un document qcq"""
	def make( self, options):
		# construit et compile
		print( " - build ")
		self.writeFileFromTemplate( self.type+'.tex', self.type+'.tex', {}, lang='latex')
		# met à jour le fichier sty (avec année, etc.)
		self.writeFileFromTemplate( 'tdtme.sty', 'tdtme.sty')
		runCommand( ["pdflatex", self.type+".tex"], 2 )
		
	def files(self, options):
		return [ self.type+".pdf"]



class DS(Session):
	"""Définit un document qcq"""
	def make( self, options):
		# construit et compile
		print( " - build ")
		self.writeFileFromTemplate( self.type+'.tex', self.type+'.tex', {}, lang='latex')
		# met à jour le fichier sty (avec année, etc.)
		self.writeFileFromTemplate( 'tdtme.sty', 'tdtme.sty')
		runCommand( ["pdflatex", self.type+".tex"], 2 )
		
	def files(self, options):
		return [ self.type+".pdf"]




class Exercice(Session):
	"""Définit un exercice"""
	def LaTeX(self):
		return self.getStringFromTemplate( 'exo.tex', lang='latex' )
	def Spip(self):
		return self.getStringFromTemplate( 'spip.txt', lang='markdown' )
