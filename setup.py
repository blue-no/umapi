from setuptools import setup

setup(
    name="umapi",
    version="0.1.0",
    license="MIT",
    description="Tool for monitoring and controlling printer via Ultimaker Api",
    author="Kota Aono",
    url="https://github.com/ut-hnl-lab/umapi.git",
    packages=['umapi'],
    install_requires=[
        'pandas',
        'requests',
        'cv2',
        'numpy'
    ]
)
