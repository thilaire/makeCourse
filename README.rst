makeCourse
----------

To use it, define a sub-class of the class `Session` with the methods `make` and `files`

    class CM(Session):
        def make(self, options):
            print( " - build handout")
            self.writeFileFromTemplate( 'CM.tex', self.name+'.tex', {} )
            runCommand( ['pdflatex', self.name+'.tex'], 2 )

        def files(self):
            return [ self.name+'.pdf' ]
