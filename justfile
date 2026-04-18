configdir := "~/.local/share/nautilus-python/extensions"
run: 
    mkdir -p {{configdir}}
    cp pompilius.py caching.py status.py links.py browser.py static {{configdir}} -r
    nautilus 
