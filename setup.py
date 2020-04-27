from setuptools import setup, find_packages
import io

def read_all(f):
    with io.open(f, encoding="utf-8") as I:
        return I.read()

requirements = list(map(str.strip, open("requirements.txt").readlines()))    
    
setup(
    name='rgsync',
    version='0.2.0',  
    description='RedisGears synchronization recipe',
    long_description=read_all("README.md"),
    long_description_content_type='text/markdown',
    classifiers=[
            'Programming Language :: Python',
            'License :: OSI Approved :: BSD License',
            'Intended Audience :: Developers',
            'Operating System :: OS Independent',
            'Development Status :: 4 - Beta',
            'Topic :: Database',
            'Programming Language :: Python :: 3.7',
    ],  # Get from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='RedisGears WriteBehind',
    author='RedisLabs',
    author_email='oss@redislabs.com',
    url='https://github.com/RedisGears/rgsync/',  
    packages=find_packages(),
    install_requires=requirements
)
