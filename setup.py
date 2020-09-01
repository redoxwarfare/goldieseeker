from setuptools import setup, find_packages
import pathlib

# Grab contents of README
# https://realpython.com/pypi-publish-python-package/#configuring-your-package
HERE = pathlib.Path(__file__).parent
README = (HERE/'README.md').read_text()

setup(
        name='goldieseeker',
        version='0.1',
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
