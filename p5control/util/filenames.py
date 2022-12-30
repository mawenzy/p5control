import os

def _filename_generator(base, width=4, end=".hdf5"):
    i = 0
    while True:
        yield f"{base}{i:0{width}d}{end}"
        i += 1

def new_filename_generator(base, width=4, end=".hdf5"):
    gen = _filename_generator(base, width, end)
    filename = next(gen)

    while True:
        if os.path.isfile(filename):
            filename = next(gen)
        else:
            yield filename

def name_generator(base, width=4, end=""):
    return _filename_generator(base, width, end)