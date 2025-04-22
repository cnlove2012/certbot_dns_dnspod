from os import path
from setuptools import setup
from setuptools import find_packages

version = "0.1.0"

install_requires = [
    "acme>=4.0.0",
    "certbot>=4.0.0",
    "tencentcloud-sdk-python-dnspod>=3.0.0",
    "setuptools",
    "requests",
    "mock",
    "requests-mock",
    "urllib3>=1.21.1,<3",
]

# read the contents of your README file

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.rst")) as f:
    long_description = f.read()

setup(
    name="certbot-dns-dnspod",
    version=version,
    description="DNSPod DNS Authenticator plugin for Certbot",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/cnlove2012/certbot_dns_dnspod",
    author="Mr.Jackin",
    author_email="cnlove2012@163.com",
    license="Apache License 2.0",
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Plugins",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Security",
        "Topic :: System :: Installation/Setup",
        "Topic :: System :: Networking",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],

    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=install_requires,
    entry_points={
        "certbot.plugins": [
            "dns-dnspod = certbot_dns_dnspod._internal.dns_dnspod:Authenticator"
        ]
    },
    # test_suite="certbot_dns_dnspod",
)
