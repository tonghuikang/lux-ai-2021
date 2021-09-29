# for setup in linux machines
# not really a script

# sudo apt-get update -y
# sudo apt-get upgrade -y
# sudo apt-get install npm rsync wget htop -y

# to install version 12 of npm
# https://stackoverflow.com/a/45584004
# curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.33.2/install.sh | bash
# export NVM_DIR="$HOME/.nvm"
# [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
# nvm install 12
# nvm use 12

# sudo may be required
npm install -g @lux-ai/2021-challenge@latest
npm install -g lux-ai-vis

# to install conda
# https://stackoverflow.com/a/28853163
# sudo apt-get install wget -y
# wget https://repo.anaconda.com/archive/Anaconda3-2020.07-Linux-x86_64.sh
# bash Anaconda3-2020.07-Linux-x86_64.sh
# (you will need to manually agree to the bash script here)

conda install jupyter ipykernel nb_conda numpy scipy requests -y
pip install kaggle-environments -U
