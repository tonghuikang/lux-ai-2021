# assuming inside specific conda environment

# to install conda
# https://stackoverflow.com/a/28853163
# wget https://repo.anaconda.com/archive/Anaconda3-2020.07-Linux-x86_64.sh
# bash Anaconda3-2020.07-Linux-x86_64.sh

conda install jupyter ipykernel nb_conda -y
conda install numpy scipy -y
conda install requests -y
pip install kaggle-environments -U

# to install npm
# sudo apt-get update -y
# sudo apt-get upgrade -y
# sudo apt-get install npm -y
# npm install -g npm
# npm install -g npm

# sudo may be required
npm install -g @lux-ai/2021-challenge@latest