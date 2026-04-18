configdir := "~/.local/share/nautilus-python/extensions"
run: 
    mkdir -p {{configdir}}
    cp pompilius.py caching.py static {{configdir}} -r
    nautilus 
