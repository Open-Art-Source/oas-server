import imghdr
import sys
import os
import tempfile
import shutil
from os import environ
from datetime import datetime
from flask import render_template, Response, current_app, request, jsonify, g
from werkzeug.utils import secure_filename
from oas import app
from oas.service.user import register, load_user_context 
from oas.service.artist import get_artwork, register_artwork
from oas.service.artwork import list_artwork
from oas.service.aimodel import compare_ipfs_content, compare_with_ipfs
from oas.model.artwork import Artwork
from oas.api.artwork import compare_ipfs
from oas.helper import get_firebase_claim, get_credential
from PIL import Image
import oas.config as oas_config
import ipfshttpclient
import json
import re
import requests

def allowed_file(filename): 
    return True

def validate_image(stream):
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')

@app.route('/compare_ipfs', methods = ['GET','POST'])
def ai_compare_ipfs():
    try:
        hash1 = request.args.get('h1')
        hash2 = request.args.get('h2')
        result = compare_ipfs(hash1, hash2)
        return Response(json.dumps({"result": result}), status=200, mimetype='application/json')
    except Exception as err:
        return Response(json.dumps({"error": str(err)}), status=200, mimetype='application/json')

@app.route('/ai_upload_file',methods=['GET','POST'])
def ai_upload_file():
    if request.method == 'POST':
        artwork_json = request.form.get('artwork')
        _artwork_info = json.loads(artwork_json or "{}")
        artwork_id = _artwork_info.get('artwork_id')
        artwork = get_artwork(dict(artwork_id=artwork_id))
        tempdir = None
        filenames = []
        try:
            # check if the post request has the file part
            #if not request.files:
            #    return Response("{}", status=200, mimetype='application/json')
            for name,files in request.files.items():
                for file in request.files.getlist(name):
                    filename = file.filename
                    # if user does not select file, browser also
                    # submit an empty part without filename
                    if file.filename == '':
                        return Response(json.dumps({"error":"no file(s)"}), status=200, mimetype='application/json')

                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        filenames.append(filename)
                        mimetype = file.mimetype
                        try:
                            if not tempdir:
                                tempdir = tempfile.mkdtemp()
                            save_to = os.path.join(tempdir, filename)
                            file.save(save_to)
                        except:
                            pass
        finally:
            if tempdir: 
                dirname = os.path.split(tempdir)[-1]
                try:
                    filename1 = os.path.join(tempdir,filenames[0])
                    filename2 = os.path.join(tempdir,filenames[1])
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
                    shutil.rmtree(tempdir, ignore_errors=True)
                    if result:
                        return Response(json.dumps({
                            "result" : result,
                            }
                            ), status=200, mimetype='application/json')
                    else:
                        return Response(json.dumps({"error": error}), status=200, mimetype='application/json')
            else: 
                return Response(json.dumps({"error":"nothing ?"}), status=200, mimetype='application/json')
                        
        return Response("{{{to}}}".format(to=save_to or tempdir), status=200, mimetype='application/json')
    return Response("what")

@app.route('/upload_file',methods=['GET','POST'])
def upload_file():
    if request.method == 'POST':
        def list_item(user, artwork, _artwork_info):
            listing = _artwork_info.get("listing")
            if listing:
                if not hasattr(listing, 'get'):
                    raise Exception("listing needs to be an object, not array")

                list_artwork(dict(artwork_id = artwork.artwork_id,
                                person_id = user.person_id,
                                #do not touch active flag
                                #active = listing.get('active') if listing.get('active') is not None else None,
                                currency = listing.get('currency'),
                                amount = listing.get('amount'),
                                ))

        tempdir = None
        filenames = []
        artwork_json = request.form.get('artwork')
        _artwork_info = json.loads(artwork_json)
        artwork_info = dict(artwork_id = _artwork_info.get('artwork_id'),
                            title=_artwork_info.get('title'),
                            medium=_artwork_info.get('medium'),
                            length=_artwork_info.get('length'),
                            width=_artwork_info.get('width'),
                            height=_artwork_info.get('height'),
                            description=_artwork_info.get('description'),
                            short_description=_artwork_info.get('short_description'),
                            dimension_unit=_artwork_info.get('dimension_unit'),
                            primary_image_file_name=_artwork_info.get('primary_image_file_name'),
                            date_created = datetime.strptime(_artwork_info.get('date_created'),'%a, %d %b %Y %H:%M:%S %Z') if _artwork_info.get('date_created') else None
                            )
        thumbnail = False
        antiforge = True
        user = None
        error = None
        try:
            # check if the post request has the file part
            #if not request.files:
            #    return Response("{}", status=200, mimetype='application/json')
            authorization = request.headers.get('Authorization')
            claims = get_firebase_claim()
            user = load_user_context(claims)
            g.user = user
            if not g.user:
                name = claims['name'].split(' ')
                g.user = register(name[0] if len(name) > 0 else None, name[-1] if len(name) > 1 else None, claims)
                user = g.user
            for name,files in request.files.items():
                for file in request.files.getlist(name):
                    filename = file.filename
                    # if user does not select file, browser also
                    # submit an empty part without filename
                    if file.filename == '':
                        return Response("{}", status=200, mimetype='application/json')

                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        filenames.append(filename)
                        mimetype = file.mimetype
                        try:
                            if not tempdir:
                                tempdir = tempfile.mkdtemp()
                            save_to = os.path.join(tempdir, filename)
                            file.save(save_to)
                            try:
                                if thumbnail:
                                    image = Image.open(save_to)
                                    max_width = 100
                                    width, height = image.size
                                    scale = width / max_width 
                                    thumb_size = (width/scale, height/scale)
                                    image.thumbnail(thumb_size, Image.ANTIALIAS)
                                    x = filename.split(".")
                                    x.insert(len(x)-1,"_thumb.")
                                    thum_filename = "".join(x)
                                    save_to_thumb = os.path.join(tempdir, thum_filename)
                                    image.save(save_to_thumb)
                                    filenames.append(save_to_thumb)
                            except:
                                pass
                        except:
                            pass
        except Exception as err:
            error = str(err)
        finally:
            if not user: 
                return Response(json.dumps({"error": str(error)}), status=200, mimetype='application/json')
            artwork = register_artwork(user.artist, Artwork.from_dict(artwork_info))
            if tempdir: 
                dirname = os.path.split(tempdir)[-1]
                with open(os.path.join(tempdir,'metadata.json'), 'w', encoding='utf-8') as f:
                    metadata = dict(
                        title = artwork.title,
                        description = artwork.description,
                        images = filenames,
                        primary_image_file_name  = artwork.primary_image_file_name or (filenames[0] if len(filenames) else None)
                        )
                    json.dump(metadata, f, ensure_ascii=False)
                try:
                    ipfs_client = ipfshttpclient.connect(oas_config.get('IPFS_API_URL'),auth=get_credential(oas_config.get('IPFS_API_CREDENTIAL')))
                    result = ipfs_client.add(tempdir, pattern="**",wrap_with_directory=False)
                    folder = result[-1]
                    hash = folder["Hash"]
                    artwork.image_files_hash = hash
                    artwork.primary_image_file_name = artwork.primary_image_file_name or (filenames[0] if len(filenames) > 0 else None)
                    register_artwork(user.artist, artwork)
                    list_item(user, artwork, _artwork_info)
                except Exception as err:
                    error = str(err)
                    result = None
                    pass
                finally:
                    shutil.rmtree(tempdir, ignore_errors=True)
                    if result:
                        return Response(json.dumps({
                            "artwork_id" : artwork.artwork_id,
                            "ipfs": [dict(Name=re.sub('^' + dirname + '/?','', x["Name"]), Hash=x["Hash"], Size=x["Size"]) for x in result]
                            }
                            ), status=200, mimetype='application/json')
                    else:
                        return Response(json.dumps({"error": str(error)}), status=200, mimetype='application/json')
            else: 
                try:
                    list_item(user, artwork, _artwork_info)
                    return Response(json.dumps({
                        "artwork_id" : artwork.artwork_id,
                        }
                        ), status=200, mimetype='application/json')
                except Exception as err:
                    error = str(err)
                    return Response(json.dumps({"error": error}), status=200, mimetype='application/json')

                        
        return Response(json.dumps({"to": save_to or tempdir}), status=200, mimetype='application/json')
    return Response(json.dumps({"error": "what"}))

