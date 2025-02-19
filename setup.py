from setuptools import setup, find_packages

setup(
    name="prompt-pack",
    version="0.2.0",
    description="A CLI to recursively filter folders/files, copy them as prompt blocks, and also reconstruct files from prompt data.",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "python-dotenv==1.0.0",
        "pyperclip==1.8.2",
        "openai==1.63.2",
    ],
    entry_points={
        "console_scripts": [
            # 'prompt-pack' => calls main() in promptpack/main.py
            "prompt-pack=promptpack.main:main",
        ],
    },
    python_requires=">=3.7",
)
