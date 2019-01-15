(require 'cl)

(when (>= emacs-major-version 24)
  (add-to-list 'package-archives '("melpa" . "http://melpa.org/packages/") t)
  )

(defvar chenlong/packages '(
			    company
			    monokai-theme
			    hungry-delete
			    swiper
			    counsel
			    smartparens
			    js2-mode
			    popwin
			    ) "Default packages")


(setq package-selected-packages chenlong/packages)

(defun chenlong/packages-installed-p ()
  (loop for pkg in chenlong/packages
	when (not (package-installed-p pkg)) do (return nil)
	finally (return t)))

(unless (chenlong/packages-installed-p)
	 (message "%s" "Refreshing package database...")
	 (package-refresh-contents)
	 (dolist (pkg chenlong/packages)
	   (when (not (package-installed-p pkg))
	     (package-install pkg))))

;;let emacs could find the executable
;;(when (memq window-system '(mac ns))
  ;;(exec-path-from-shell-initialize))

(global-hungry-delete-mode)

;;(add-hook 'emacs-lisp-mode-hook 'smartparens-mode)
(smartparens-global-mode t)

(ivy-mode 1)
(setq ivy-use-virtual-buffers t)


(setq auto-mode-alist
      (append
       '(("\\.js\\'" . js2-mode))
       auto-mode-alist))

(global-company-mode t)

(load-theme 'monokai t)

(require 'popwin)
(popwin-mode t)

(provide 'init-packages)
