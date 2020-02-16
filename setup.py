from setuptools import setup, find_packages
setup(
    name='RedisGearsWriteBehind',
    version='0.1',
    packages=find_packages(),
    install_requires=[
    	'SQLAlchemy',
    ]
)
