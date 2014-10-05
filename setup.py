from setuptools import setup, find_packages

setup(
    name = "simtool",
    version = "0.0.1",
    author = "Alan Shi",
    author_email = "alan@sinosims.com",

    packages = find_packages(), 
    include_package_data = True,

    url = "http://www.sinosims.com",
    description = "Simcore Tools Client",
    
    entry_points = {
        'console_scripts': [ 'simtool = simtool.run:main' ]
    },
)
