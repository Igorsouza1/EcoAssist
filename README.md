[![status](https://joss.theoj.org/papers/dabe3753aae2692d9908166a7ce80e6e/status.svg)](https://joss.theoj.org/papers/dabe3753aae2692d9908166a7ce80e6e)
[![Project Status: Active The project has reached a stable, usable state
and is being actively
developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
![GitHub](https://img.shields.io/github/license/PetervanLunteren/EcoAssist)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7223363.svg)](https://doi.org/10.5281/zenodo.7223363)
![GitHub last
commit](https://img.shields.io/github/last-commit/PetervanLunteren/EcoAssist)

<p align="center">
  <img src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/logo_large.png" width=60% height="auto" />
</p>

<h2 align="center">Simplifying camera trap image analysis for ecologists</h2>

EcoAssist is an open-source application designed to streamline the work of ecologists dealing with camera trap images. It's an AI platform that enables annotation, training, and deployment of custom models for automatic species detection, offering ecologists a way to save time reviewing images and focus on conservation efforts.

[<img align="right" alt="alt_text" width="25%" src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/Logo_Social_Smartparks-01.png" /> ](https://www.smartparks.org/)

Recently, I joined forces with [Smart Parks](https://www.smartparks.org/). We’re working on expanding the software to create a robust toolkit for camera trap image analysis to be used by ecologists worldwide.
<!--- You can support this initiative by contributing through the sponsorship button below. --->
Our current focus is:
* Implementing a human-in-the-loop feature for result verification.
* Improving the annotation process to make it more robust.
* Testing the setup with a real-world use-case for [the Desert Lion Conservation](https://www.desertlion.info/) project.
* Set up personalized assistance to support ecologists in effectively using EcoAssist for their projects.
* Exploring the possibility of providing optimized hardware support.

You can help me by letting me know about any improvements, bugs, or new features so that I can keep EcoAssist up-to-date. You can [raise an issue](https://github.com/PetervanLunteren/EcoAssist/issues/new) or [email me](mailto:petervanlunteren@hotmail.com). An e-mail just to say hi and tell me about your project is also very much appreciated!

## Quick links
1. [Demo](#demo)
2. [Overview](#overview)
3. [Main features](#main-features)
4. [Teasers](#teasers)
5. [Users](#users)
6. [Tutorial](#tutorial)
7. [Requirements](#requirements)
8. [Download](#download)
9. [Test your installation](#test-your-installation)
10. [Update](#update)
11. [GPU support](#gpu-support)
12. [Bugs](#bugs)
13. [Cite](#cite)
14. [Uninstall](#uninstall)
15. [Contributors](#contributors)
16. [Similar software](#similar-software)

## Demo
<p align="center">
  <img src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/demo.gif" width=60% height="auto" />
</p>

## Overview
<p align="center">
  <img src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/overview.png" width=100% height="auto" />
</p>

## Main features
* Runs on Windows, Mac, and Linux
* No admin rights required
* After installation completely offline
* Use [MegaDetector](https://github.com/ecologize/CameraTraps/blob/main/megadetector.md) to filter out empty images or videos
* Integration with [Timelapse](https://saul.cpsc.ucalgary.ca/timelapse/)
* English :gb: & Español :es:
* Train models using the [YOLOv5](https://github.com/ultralytics/yolov5) architecture
* Deploy models on images or videos
* Built in function to annotate images based on [labelImg](https://github.com/heartexlabs/labelImg)
* GPU acceleration for NVIDIA and Apple Silicon
* Post-process your data to
  * separate
  * visualise
  * crop
  * label
  * export to .csv

## Teasers
<p align="center">
  <img src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/teaser_animal.jpg" width=45% height="auto" />
  <img src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/teaser_red_fox.JPG" width=45% height="auto" />
  <img src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/teaser_ocelot.JPG" width=45% height="auto" /> 
  <img src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/teaser_tinamou.JPG" width=45% height="auto" /> 
</p>

Camera trap images taken from the [Missouri camera trap database](https://lila.science/datasets/missouricameratraps) and the [WCS Camera Traps dataset](https://lila.science/datasets/wcscameratraps).

## Users
<p align="center">
  <img src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/cummulative_users.png" width=60% height="auto" />
</p>
<p align="center">
  <img src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/users.png" width=60% height="auto" />
</p>

Are you also a user and not on this map? [Let me know](mailto:petervanlunteren@hotmail.com)!

## Tutorial
I've written a detailed tutorial on Medium that provides a step-by-step guide on annotating, training, evaluating, deploying, and postprocessing data with EcoAssist. You can find it [here](https://medium.com/towards-artificial-intelligence/train-and-deploy-custom-object-detection-models-without-a-single-line-of-code-a65e58b57b03). 

## Requirements
Except a minimum of 8 GB RAM, there are no hard system requirements for EcoAssist since it is largely hardware-agnostic. However, please note that machine learning can ask quite a lot from your computer in terms of processing power. Although it will run on an old laptop only designed for text editing, it’s probably not going to train any accurate models, while deploying models can take ages. Generally speaking, the faster the machine, the more reliable the results. GPU acceleration is a big plus.

## Download
EcoAssist will install quite a lot of dependencies, so don't panic if the installation takes 10-20 minutes and generates lots of textual feedback as it does so. Please note that some antivirus, VPN, proxy servers or other protection software might interfere with the installation. If you're having trouble, please disable this protection software for the duration of the installation.

Opening EcoAssist for the first time will take a bit longer than usual due to script compiling. Have patience, all subsequent times will be better.

#### Windows installation
1. EcoAssist requires Git and a conda distribution to be installed on your device. See below for instructions on how to install them. During installation, you can leave all parameters at their default values. Just keep track of the destination directories (for example, `C:\Program Files\Git` and `C:\ProgramData\miniforge3`). You might have to specify these paths later on.
    * You can install Git from [gitforwindows.org](https://gitforwindows.org/). 
    * EcoAssist will work with Anaconda, Miniconda or Miniforge. Miniforge is recommended, however, Anaconda or Miniconda will suffice if you already have that installed. To install Miniforge, simply download and execute the [Miniforge installer](https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe). If you see a "Windows protected your PC" warning, you may need to click "More info" and "run anyway".
2. Download the [EcoAssist installation file](https://PetervanLunteren.github.io/EcoAssist/install.bat) and double-click it. If that doesn't work, you can drag and drop it in a command prompt window and press enter.
3. If you've executed it with admin rights, it will be installed for all users. If you don't have admin rights, you will be prompted if you'd still like to enter an admin password, or proceed with the non-admin install - which will make EcoAssist available for your user only.
4. EcoAssist will try to locate your Git and conda distribution. If it fails to find them automatically, you'll have to enter the paths to the installations from step 1 when prompted, or just drag and drop the installation folders into the console window.
5. When the installation is finished, there will be a shortcut file in your `Downloads` folder. You are free to move this file to a more convenient location. EcoAssist will open when double-clicked.

#### Mac installation
1. Download and open [this file](https://PetervanLunteren.github.io/EcoAssist/install.command). Some computers can be quite reluctant when having to open command files downloaded from the internet. You can circumvent trust issues by opening it with right-click > open > open. If that still doesn't work, you can change the file permissions by opening a new terminal window and copy-pasting the following commands.
```bash
chmod 755 $HOME/Downloads/install.command
bash $HOME/Downloads/install.command
```
2. If you're an Apple Silicon user (M1/M2), go for a nice walk because this may take about 30 minutes to complete. Some of the software packages are not yet adopted to the Apple Silicon processor. There is a workaround, but it takes some time. In order to make MegaDetector work on Apple Silicon computers, the guys at [Ecologize](http://ecologize.org/) had to re-build the model with *slightly* different results. The bounding boxes appear to be the same to around two decimal places in both location and confidence, which is good, but not *exactly* the same. Please keep in mind that this is an unvalidated version of MegaDetector, and they don't exactly know how it compares to the validated version since it is much less tested.
4. When the installation is done, you'll find a `EcoAssist.command` file in your `Applications` folder. The app will open when double-clicked. You are free to move this file to a more convenient location. If you want EcoAssist in your dock, manually change `EcoAssist.command` to `EcoAssist.app`, then drag and drop it in your dock and change it back to `EcoAssist.command`. Not the prettiest solution, but it works...

#### Linux installation
1. Download [this file](https://PetervanLunteren.github.io/EcoAssist/install.command).
2. Change the permission of the file and execute it by running the following commands in a new terminal window. If you don't have root privileges, you might be prompted for a password to install `libxcb-xinerama0`. This package is required for the labelImg software on some Linux versions. If you don't know the `sudo` password, you can skip this by pressing Ctrl+D when you are prompted for the password. EcoAssist will still work fine without it, but you might have problems with the labelImg software. The rest of the installation can be done without root privileges.
```bash
chmod 755 $HOME/Downloads/install.command
bash $HOME/Downloads/install.command
```
3. During the installation, a file called `EcoAssist` will be created on your desktop. The app will open when double-clicked. You are free to move this file to a more convenient location.

## Test your installation
<p align="center">
  <img src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/test-installation.png" width=90% height="auto" >
</p>

You can quickly verify its functionality by following the steps below.
1. Choose a local copy of [this](https://drive.google.com/uc?export=download&id=1ZNAhMbWVoLuIlkejI0ydS1XVChYSCQ50) (unzipped) folder at step 1
2. Check 'Process all images in the folder specified' 
3. Click the 'Deploy model' button and wait for the prcess to complete
4. Select the `test-images` folder again as 'Destination folder'
5. Check 'Export results to csv files'
6. Click the 'Post-process files' button

If all went well, there should be a file called `results_files.csv` with the following content. 

| absolute_path | relative_path | data_type | n_detections | max_confidence |
| :--- | :--- | :--- | :--- | :--- |
| /.../test-images  | empty.jpg  | img | 0 | 0.0 |
| /.../test-images  | person.jpg  | img | 2 | 0.875 |
| /.../test-images  | mutiple_categories.jpg  | img | 2 | 0.899 |
| /.../test-images  | animal.jpg  | img | 1 | 0.844 |
| /.../test-images  | vehicle.jpg  | img | 1 | 0.936 |

## Update
To update to the latest version, you'll have to repeat the [download](#download) procedure. It will replace all the old EcoAssist files with the new ones. It's all automatic, you don't have to do anything. Don't worry, it won't touch your conda distribution or your Git installation. Just the `ecoassistcondaenv` environment. 

## GPU support
EcoAssist will automatically run on NVIDIA or Apple Silicon GPU if available. The appropriate `CUDAtoolkit` and `cuDNN` software is already included in the EcoAssist installation for Windows and Linux. If you have NVIDIA GPU available but it doesn't recognise it, make sure you have a [recent driver](https://www.nvidia.com/en-us/geforce/drivers/) installed, then reboot. An MPS compatible version of `Pytorch` is included in the installation for Apple Silicon users. Please note that applying machine learning on Apple Silicon GPU's is still under beta version. That means that you might run into errors when trying to run on GPU. My experience is that deployment runs smoothly on GPU, but training throws errors. Training on CPU will of course still work. The progress window and console output will display whether EcoAssist is running on CPU or GPU. 

<p align="center">
  <img src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/progress_window.png" width=50% height="auto" >
  <img src="https://github.com/PetervanLunteren/EcoAssist-metadata/blob/main/imgs/Training_on_GPU.png" width=90% height="auto" >
</p>

## Bugs
If you encounter any bugs, please [raise an issue](https://github.com/PetervanLunteren/EcoAssist/issues) in this repository or [send me an email](mailto:petervanlunteren@hotmail.com).

## Cite
Please use the following citations if you used EcoAssist in your research.
#### EcoAssist citation
```BibTeX
@software{van_Lunteren_EcoAssist_2022,
  title     = {{EcoAssist: A no-code platform to train and deploy YOLOv5 object detection and the MegaDetector model}},
  author    = {van Lunteren, Peter},
  year      = {2022},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.7223363},
  url       = {https://github.com/PetervanLunteren/EcoAssist}
}
```

#### MegaDetector citation
If you used the MegaDetector model to analyse images or retrain your model.
```BibTex
@article{Beery_Efficient_2019,
  title     = {Efficient Pipeline for Camera Trap Image Review},
  author    = {Beery, Sara and Morris, Dan and Yang, Siyu},
  journal   = {arXiv preprint arXiv:1907.06772},
  year      = {2019}
}
```

#### Ultralytics citation
If you trained or retrained a model.
```Bibtex
@software{Jocher_YOLOv5_2020,
  title = {{YOLOv5 by Ultralytics}},
  author = {Jocher, Glenn},
  year = {2020},
  doi = {10.5281/zenodo.3908559},
  url = {https://github.com/ultralytics/yolov5},
  license = {AGPL-3.0}
}
```

## Uninstall
All files are located in one folder, called `EcoAssist_files`. You can uninstall EcoAssist by simply deleting this folder. Please be aware that it's hidden, so you'll probably have to adjust your settings before you can see it (find out how to: [macOS](https://www.sonarworks.com/support/sonarworks/360003040160-Troubleshooting/360003204140-FAQ/5005750481554-How-to-show-hidden-files-Mac-and-Windows-), [Windows](https://support.microsoft.com/en-us/windows/view-hidden-files-and-folders-in-windows-97fbc472-c603-9d90-91d0-1166d1d9f4b5#WindowsVersion=Windows_11), [Linux](https://askubuntu.com/questions/232649/how-to-show-or-hide-a-hidden-file)). If you're planning on updating EcoAssist, there is no need to uninstall it first. It will do that automatically. More about updating [here](#update). 
```r
# Windows (all users)
─── 📁Program Files
    └── 📁EcoAssist_files

# Windows (single user)
─── 📁Users
    └── 📁<username>
        └── 📁EcoAssist_files

# macOS
─── 📁Applications
    └── 📁.EcoAssist_files

# Linux
─── 📁home
    └── 📁<username>
        └── 📁.EcoAssist_files
```


## Contributors
This is an open-source project, so please feel free to fork this repo and submit fixes, improvements or add new features. For more information, see the [contribution guidelines](https://github.com/PetervanLunteren/EcoAssist/blob/main/CONTRIBUTING.md). 

<a href="https://github.com/petervanlunteren/EcoAssist/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=petervanlunteren/EcoAssist" />
</a>

###
Thank you for your contributions!

## Similar software
As far as I know, there are three other software packages capable of deploying the `MegaDetector` model. These packages are all set up slightly different and have different features.
* [CamTrap Detector](https://github.com/bencevans/camtrap-detector)
* [MegaDetector GUI](https://github.com/petargyurov/megadetector-gui)
* [Megadetector-Interface](https://github.com/NaomiMcWilliam/Megadetector-Interface)
