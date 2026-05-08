#!/bin/bash

#安装homebrew
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

#安装常用软件
brew cask install google-chrome #chrome
brew cask install sogouinput #搜狗输入法
brew cask install qq #qq
brew cask install qqmusic #qq音乐
brew cask install neteasemusic #网易云音乐
brew cask install shadowsocksx-ng #shadowsocksx-ng
brew cask install wireshark #wireshark
brew cask install zenmap #zenmap
brew cask install sourcetree #sourcetree
brew cask install mat #mat
brew cask install typora #typora
brew cask install visual-studio-code #visual studio code
brew cask install intellij-idea #idea
brew cask install iterm2 #iterm2
brew cask install anaconda #anaconda
brew cask install docker #docker

#安装常用命令行工具
brew install coreutils #linux核心包
brew install gradle #gradle
brew install autojump #autojump
brew install tmux #tmux

mkdir -p ~/gitrepo
cd ~/gitrepo
git clone https://github.com/MrChen1993/dotfiles.git
sh -c "$(curl -fsSL https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
mv ~/.zshrc ~/.zshrc.bak
ln -s ~/dotfiles/zshrc ~/.zshrc

git clone https://github.com/seebi/dircolors-solarized.git ~/.dircolors-solarized
sudo chsh -s /bin/zsh
