from typing import BinaryIO, List, Any
import os
from io import open
import tempfile
import shutil
import ipfshttpclient
import json
import oas.config as oas_config
from oas.helper import get_firebase_claim, get_credential

class FileObject:
    file: BinaryIO
    filename: str
    mimetype: str

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def cloud_save(files:List[FileObject]) -> Any:
    tempdir = None
    for file in files:
        filename = file.filename
        fs = file.file
        if not tempdir:
            tempdir = tempfile.mkdtemp()
        save_to = os.path.join(tempdir, filename)
        with open(save_to, 'wb') as f:
            shutil.copyfileobj(fs, f, length=131072)

    if not tempdir: return []
    try:
        ipfs_client = ipfshttpclient.connect(oas_config.get('IPFS_API_URL'),auth=get_credential(oas_config.get('IPFS_API_CREDENTIAL')))
        result = ipfs_client.add(tempdir,wrap_with_directory=False)
        return result
    except Exception as err:
        error = str(err)
        result = None
        pass
    finally:
        try:
            shutil.rmtree(tempdir, ignore_errors=True)
        except:
            pass
