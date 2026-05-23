configdir := "~/.local/share/nautilus-python/extensions"
run: 
    mkdir -p {{configdir}}
    rm -f {{configdir}}/*.py
    cp pompilius.py caching.py status.py links.py browser.py profiles_dialog.py add_profile_dialog.py static {{configdir}} -r
    nautilus 
