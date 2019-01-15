(setq right-bell-function 'ignore)

(global-auto-revert-mode t)

(global-linum-mode t)

(abbrev-mode t)
(define-abbrev-table 'global-abbrev-table '(
					    ("mrchen1993" "mrchen1993")
					    ))

(setq make-backup-files nil)

(setq auto-save-default nil)

(require 'recentf)
(recentf-mode 1)
(setq recentf-max-menu-item 25)

(add-hook 'emacs-lisp-mode-hook 'show-paren-mode)

(delete-selection-mode t)

(setq enable-recursive-minibuffers t)

(provide 'init-better-defaults)
