from setuptools import setup, find_packages

setup(
        name='goldieseeker',
        description='A command-line tool for generating and evaluating Goldie Seeking strategies',
        version='0.1',
        author='redoxwarfare',
        url='https://github.com/redoxwarfare/goldieseeker',
        packages=find_packages(),
        package_data={'goldieseeker': ['maps/*.csv', 'maps/*.txt', 'images/*.png']},
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
        },
        classifiers=[
                'Programming Language :: Python :: 3',
                'License :: OSI Approved :: MIT License',
                'Development Status :: 4 - Beta'
        ]
)
