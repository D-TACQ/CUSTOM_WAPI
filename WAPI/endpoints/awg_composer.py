#!/usr/bin/env python3

import os
import threading
import re
import json
import time
import waves.build_templates as build_templates


class globals:
    compose_status = [False, None]
    root_dir = '/tmp/AWG/'
    last_file = 'filename.dat'


##actions
def handle_build_template(lines, **kwargs):
    print('handle_build_template')
    return build_templates.from_array(lines)

def handle_run_composer(output, pattern, nrep='', segment='', **kwargs):
    print('handle_run_composer')
    print(f"output {output}")
    print(f"output {pattern}")
    print(f"output {nrep}")
    if globals.compose_status[0]:
        return False, f"Compose Running"
    if not get_manifest():
        return False, f"No Manifest"
    
    awg_outputs = ['oneshot_rearm', 'oneshot', 'continuous']

    if output in awg_outputs:
        output = f"--awg_mode {output}"
    else:
        globals.last_file = f"{escape_input(output)}.dat"
        output = f"-o /tmp/{globals.last_file}"
    if nrep:
        nrep = f"--nreps {escape_input(nrep)}"

    if segment:
        segment = f"--abcde {escape_input(segment)}"

    pattern = escape_input(pattern)
    cmd = f"/usr/local/bin/awg_composer {output} {nrep} {segment} {pattern}"
    print(f"Running CMD: {cmd}")
    threading.Thread(target=run_compose, args=(cmd,)).start()
    return True, f"Compose started {cmd}"

def handle_erase_mainfest(**kwargs):
    print('handle_erase_mainfest')
    os.system(f"rm -rf {globals.root_dir}")
    return True, 'mainfest erased'

def handle_lpp_rearm(rearm_num, **kwargs):
    print('handle_lpp_rearm')
    if not (0 <= int(rearm_num) <= 32):
        return False, 'lpp_rearm value out of range'
    os.system(f"set.site 0 lpp_rearm {rearm_num}")
    return True, f"lpp_rearm set to {rearm_num}"

def handle_trigger_soft_trigger(**kwargs):
    print('handle_trigger_soft_trigger')
    os.system(f"set.site 0 soft_trigger")
    return True, 'Triggered'


#state routes
def handle_manifest(response, api):
    manifest = get_manifest()
    if manifest:
        response.content_type = 'text/plain'
        response.body = manifest
        return response
    response.status = 404
    response.body = 'None'
    return response

def handle_compose_status(response, api):
    print('handle_compose_status')
    response.body = json.dumps({'compose_status': globals.compose_status})
    response.content_type = 'application/json'
    return response

def handle_compose_download(response, api):
    print('handle_compose_download')
    max_size = 20 # MB
    url_base = 'composed_file'
    filepath = os.path.join('/tmp/', globals.last_file)
    symlink = os.path.join(api.web_dir, url_base)
    response.status = 404
    if not os.path.exists(filepath):
        response.body = json.dumps({'error': 'No File'})
        return response
    if globals.compose_status[0]:
        response.body = json.dumps({'error': 'Compose in progress'})
        return response
    file_size = round(os.stat(filepath).st_size / (1024 * 1024), 2)
    if file_size > max_size:
        response.body = json.dumps({'error': 'File exceeds size limit'})
        return response
    if os.path.islink(symlink):
        if os.readlink(symlink) != filepath:
            os.unlink(symlink)
            os.symlink(filepath, symlink)
    else:
        os.symlink(filepath, symlink)
    response.status = 200
    payload = {
        'url' : url_base,
        'filename': globals.last_file
    }
    response.body = json.dumps(payload)
    return response

#helper functions
def escape_input(user_input):
    colons_slashes = r"[;:\/]*"
    return re.sub(colons_slashes, '', user_input)

def get_manifest():
    filepath = '/tmp/AWG/MANIFEST'
    if not os.path.isfile(filepath) :
        return False
    with open(filepath) as f:
       return f.read()
    
def run_compose(cmd):
    start_time = time.time()
    globals.compose_status[0] = True
    globals.compose_status[1] = 'Composing'
    print(f"[COMPOSER] Running {cmd}")
    return_code = os.system(cmd)
    print(f"[COMPOSER] Finished")
    globals.compose_status[0] = False
    if return_code > 0:
        print(f"Errored {return_code}")
        globals.compose_status[1] = 'Errored'
        return
    globals.compose_status[1] = f"Done {round(time.time() - start_time, 2)}s"


##manifest
manifest = {
    'name' : 'AWG Composer',
    'html' : 'awg_composer.html',
    'actions': {
        'build_template': handle_build_template,
        'awg_compose': handle_run_composer,
        'erase_mainfest': handle_erase_mainfest,
        'lpp_rearm' : handle_lpp_rearm,
        'trigger_soft_trigger' : handle_trigger_soft_trigger,
    },
    'states': {
        'manifest' : handle_manifest,
        'compose_status' : handle_compose_status,
        'compose_download' : handle_compose_download,
    },
}