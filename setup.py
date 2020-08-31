from setuptools import setup, find_packages

setup(
        name='goldieseeker',
        description='A command-line tool for generating and evaluating Goldie Seeking strategies',
        version='0.1',
        author='redoxwarfare',
        url='https://github.com/redoxwarfare/goldieseeker',
        packages=find_packages(),
        install_requires=[
                'click',
                'networkx',
                'matplotlib',
                'numpy',
                'scipy',
                'pyparsing'
        ],
        entry_points="""
            [console_scripts]
            gseek=goldieseeker:cli
        """,
        classifiers=[
                'Programming Language :: Python :: 3',
                'License :: OSI Approved :: MIT License',
                'Development Status :: 4 - Beta'
        ]
)
