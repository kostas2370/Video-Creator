import os, sys
import shutil
from pathlib import Path

try:
    from bing import Bing
except ImportError:  # Python 3
    from .bing import Bing


def download(query, limit=100, output_dir='dataset', adult_filter_off=True, 
             force_replace=False, timeout=60, filter="", verbose=True):

    # engine = 'bing'
    if adult_filter_off:
        adult = 'off'
    else:
        adult = 'on'

    image_dir = Path(output_dir).absolute()


    # check directory and create if necessary
    try:
        if not Path.is_dir(image_dir):
            Path.mkdir(image_dir, parents=True)

    except Exception as e:
        print('[Error]Failed to create directory.', e)
        sys.exit(1)
        
    bing = Bing(query, limit, image_dir, adult, timeout, filter, verbose)
    kk = bing.run()
    return kk


if __name__ == '__main__':
    download('dog', output_dir="..\\Users\\cat", limit=10, timeout=1)
