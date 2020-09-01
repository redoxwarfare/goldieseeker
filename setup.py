from setuptools import setup, find_packages
import pathlib
import re

# Grab contents of README
# https://realpython.com/pypi-publish-python-package/#configuring-your-package
HERE = pathlib.Path(__file__).parent
README = (HERE/'README.md').read_text()

# https://stackoverflow.com/a/41110107
INIT = (HERE/'goldieseeker/__init__.py').read_text()
def get_from_init(property):
    result = re.search(fr'{property}\s*=\s*[\'"]([^\'"]*)[\'"]', INIT)
    return result.group(1)


setup(
        name='goldieseeker',
        version=get_from_init('__version__'),
        description='A command-line tool for generating and evaluating Goldie Seeking strategies',
        long_description=README,
        long_description_content_type='text/markdown',
        author='redoxwarfare',
        url='https://github.com/redoxwarfare/goldieseeker',
        license='MIT',
        classifiers=[
                'Programming Language :: Python :: 3',
                'License :: OSI Approved :: MIT License',
                'Development Status :: 4 - Beta'
        ],
        packages=find_packages(),
        package_data={'goldieseeker': ['maps/*.csv', 'maps/*.txt', 'images/*.png']},
        include_package_data=True,
        python_requires='>=3.6',
        install_requires=[
                'click',
                'networkx',
                'matplotlib',
                'numpy',
                'scipy',
                'pyparsing'
        ],
        entry_points={
                'console_scripts': [
                        'gseek = goldieseeker.__main__:main'
                ]
        }
)
