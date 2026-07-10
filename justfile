configdir := "~/.local/share/nautilus-python/extensions"
run:
    mkdir -p {{configdir}}
    rm -f {{configdir}}/*.py
    cp src/dialog/*.py src/menu/*.py src/overlay/*.py src/*.py static {{configdir}} -r
    nautilus
