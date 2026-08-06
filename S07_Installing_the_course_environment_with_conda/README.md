# Installing the course environment(s) with conda
Gareth Funning, University of California, Riverside

To use the course materials past the end of the course and closing of access to OpenScienceLab, you will need to install an environment that can support the various software packages and tools that the course makes use of. Luckily for us, it only takes a few simple `conda` (or `conda`'s faster cousin, `mamba`) commands to get the job done.

These instructions assume that you have an operating system with terminal access $-$ a Linux operating system, a Windows operating system with the WSL (Windows Subsystem for Linux) installed, or MacOS.

[Instructions for installing last year's course environments, which include processing using isce2](./2025_environment_instructions.md), are included here for posterity.

## 1. Install miniforge
`miniforge` is the fully open source cousin of the `miniconda` package installer. It draws natively from the open source conda-forge package repository, in which many of the major packages we use in the course reside.

This is easy enough to do! Simply go to the `miniforge` Github site ([https://github.com/conda-forge/miniforge](https://github.com/conda-forge/miniforge)) and follow the instructions there for the operating system of your choice. (For WSL, you should download the Linux version, which will work fine in WSL.)
If you already have `miniconda` installed, you can still use it, but I highly recommend installing `mamba` to use with it if you haven't already.

## 2. Download the environment file
Included in this directory is an environment (yml) file based on the 2026 course environment $-$ [isceplus2026.yml](./isceplus2026.yml). This is essentially a list of the packages that you want `conda`/`mamba` and `pip` to install on your system. Download it to a place where you will be able to find it in the terminal. 

## 3. Install the environment using mamba
Navigate to the location of your downloaded environment file, and run a command like this:
```
mamba env create -f isceplus2026.yml
```
(Or substitute the name of the environment file you'd like to install instead, if you have another one. If, for some inexplicable reason, you didn't install `mamba` then you can run the above command with `conda` instad of `mamba`, but it will take a lot longer.) This will create an environment with the name included in the top of the yml file on your system. For the [isceplus2026.yml](./isceplus2026.yml) file, this is `earthscope_insar`, as used in the course. (If you don't like that name, edit the yml file and change the 'name'!) 

## 4. Finish up your setup
Some packages you have installed expect files to be on your path. So we can write some configuration scripts that set up those things.

### For mintpy
Post-installation setup instructions can be found here: [https://github.com/insarlab/MintPy/blob/main/docs/installation.md](https://github.com/insarlab/MintPy/blob/main/docs/installation.md)

## 5. Let's go!
Assuming that everything worked, then you can start to use your new environment. First you need to activate it:
```
conda activate earthscope_insar
```
And then, go to a directory containing Jupyter notebooks and open Jupyter!
```
jupyter notebook
```

## 6. You probably want to download all of the Jupyter notebooks used in the course
You want all of these great teaching materials, yes? Including these instructions? If so, navigate to the place on your file system where you want to store them, and run this to clone them:
```
git clone https://github.com/isceplus/2026-isceplus.git
```
The place where you download these would probably be a good place to start up Jupyter!

## Repositories of commonly-used packages
For more details of packages and their installation, go to the source!
* isce3: https://github.com/isce-framework/isce3
* mintpy: https://github.com/insarlab/MintPy
* Dolphin: https://github.com/isce-framework/dolphin
