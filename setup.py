from setuptools import setup, find_packages


setup(
    name="eldrax",
    version="0.1a2",
    packages=find_packages(),
    zip_safe=False,
    install_requires=[
        "requests==1.2.3",
    ],
)
