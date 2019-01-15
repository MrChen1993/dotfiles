if &compatible
  set nocompatible
endif
" Add the dein installation directory into runtimepath
set runtimepath+=~/.cache/dein/repos/github.com/Shougo/dein.vim

if dein#load_state('~/.cache/dein')
  call dein#begin('~/.cache/dein')

  call dein#add('~/.cache/dein')
  call dein#add('altercation/vim-colors-solarized')
  call dein#add('yianwillis/macvimcdoc')

  call dein#end()
  call dein#save_state()
endif

filetype plugin indent on
syntax enable
set number
set relativenumber

" 设置vim颜色为solarized, 当运行在gui下,使用亮色
set background=dark
if(has ("gui_running"))
  set background=light
  set guifont=Source\ Code\ Pro\:h14
endif
colorscheme solarized

inoremap jj <Esc>
inoremap <C-A> <Home>
inoremap <C-E> <End>
inoremap <C-F> <Right>
inoremap <C-B> <Left>

