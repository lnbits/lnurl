from os import path
from setuptools import setup


with open(path.join(path.abspath(path.dirname(__file__)), 'README.md')) as f:
    long_description = f.read()


setup(
    name='lnurl',
    version='0.1.0',
    url='https://github.com/python-ln/lnurl',
    author="jogco",
    author_email="jogco@lnsms.world",
    license='MIT',
    description='LNURL implementation for Python.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='bitcoin lightning-network lnurl',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Utilities',
    ],
    packages=['lnurl'],
    install_requires=[
        'bech32',
    ],
    zip_safe=False
)
