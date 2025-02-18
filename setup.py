from setuptools import setup, find_packages

setup(
    name="prompt-pack",
    version="0.1.0",
    description="A CLI to recursively filter folders/files and copy them as prompt blocks.",
    packages=find_packages(),  # will find the 'promptpack' package
    include_package_data=True,
    install_requires=[
        "python-dotenv==1.0.0",
        "pyperclip==1.8.2",
    ],
    entry_points={
        "console_scripts": [
            # 'prompt-pack' is the command, which runs main() in promptpack/main.py
            "prompt-pack=promptpack.main:main",
        ],
    },
    python_requires=">=3.7",
)
