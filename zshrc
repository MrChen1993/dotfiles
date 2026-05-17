export ZSH=$HOME/.oh-my-zsh
ZSH_THEME="robbyrussell"
DEFAULT_USER="chenlong"
plugins=(
  git
  brew
  autojump
  colored-man-pages
  zsh-syntax-highlighting
  extract
  sudo
  zsh-autosuggestions
)
# oh-my-zsh 后台静默自动更新，每 30 天检查一次
zstyle ':omz:update' mode auto
zstyle ':omz:update' frequency 30

source $ZSH/oh-my-zsh.sh
source ~/.customerc
