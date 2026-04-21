configdir := "~/.local/share/nautilus-python/extensions"
run: 
    mkdir -p {{configdir}}
    cp pompilius.py caching.py status.py links.py browser.py profiles_dialog.py providers_dialog.py static {{configdir}} -r
    nautilus 
