from setuptools import setup, find_packages

setup(
    name="umapi",
    version="0.3.0",
    license="MIT",
    description="Tool for monitoring and controlling printer via Ultimaker Api",
    author="Kota Aono",
    url="https://github.com/ut-hnl-lab/umapi.git",
    package_data={"": ["*.json"]},
    packages=find_packages()
)
