from PIL import Image
from typing import Any, Dict, List, Union, NoReturn, Optional, Tuple
import oas.config as oas_config
import ipfshttpclient
import json
import re
import requests
import os
import shutil
import tempfile

def _download_file(dir:str, url:str, filename:str) -> str:
    local_filename = os.path.join(dir,filename)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                #if chunk: 
                f.write(chunk)
            f.close()
    return local_filename

def compare_with_ipfs(item_url:str, tempdir:str, filename:str) -> Any:
    try:
        filename1 = _download_file(tempdir, item_url, 'ipfs1')
        filename2 = filename
        files = {
            'image-0': open(filename1, 'rb'),
            'image-1': open(filename2, 'rb'),
            }
        pytorch_endpoint = oas_config.get('PYTORCH_URL')
        pytorch_model_endpoint = f'{pytorch_endpoint}/image_dissimilarity'
        r = requests.post(pytorch_model_endpoint, files = files)
        result = r.json()
    except Exception as err:
        error = str(err)
        result = None
        pass
    finally:
        if result:
            if type(result) is dict:
                return result
            else:
                return f'{result:9.20f}'
        else:
            return error

def compare_ipfs_content(item1_url:str, item2_url:str) -> Any:
    tempdir = None
    try:
        tempdir = tempfile.mkdtemp()
        dirname = os.path.split(tempdir)[-1]
        filename = _download_file(tempdir, item2_url, 'ipfs2')
        result = compare_with_ipfs(item1_url, tempdir, filename)
    except Exception as err:
        error = str(err)
        result = None
        pass
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)
        if result:
            return result
        else:
            return error
