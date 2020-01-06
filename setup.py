from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='makeCourse',
      version='0.5.1',
	description='A tool to build a course (from list of exercices, lectures, etc.)',
      long_description=readme(),
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Topic :: Education',
        'Topic :: Text Processing :: Markup :: LaTeX',
        'Intended Audience :: Science/Research'
      ],
      keywords='latex lectures course',
      url='https://github.com/thilaire/makeCourse',
      author='Thibault Hilaire',
      author_email='thibault@docmatic.fr',
      license='MIT',
      packages=['makeCourse'],
      install_requires=[ 'pypandoc', 'colorama', 'beautifulsoup4', 'lxml', 'Jinja2', 'requests' ],
      include_package_data=True,
      zip_safe=False)
