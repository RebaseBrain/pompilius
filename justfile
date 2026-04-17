configdir := "~/.local/share/nautilus-python/extensions"
run: 
    mkdir -p {{configdir}}
    cp pompilius.py static {{configdir}} -r
    nautilus 
