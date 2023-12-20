#!/usr/bin/env python3

import os
import threading
import re
import json
import time
import subprocess
import waves.build_templates as build_templates


class globals:
    compose_status = [False, None]
    root_dir = '/tmp/AWG/'
    last_file = 'filename.dat'
    last_compose = {}


##actions
def handle_build_template(lines, **kwargs):
    print('handle_build_template')
    return build_templates.from_array(lines)

def handle_run_composer(output, pattern, nreps='', segment='', **kwargs):
    print('handle_run_composer')
    print(f"output {output}")
    print(f"output {pattern}")
    print(f"output {nreps}")
    if globals.compose_status[0]:
        return False, f"Compose Running"
    if not get_manifest():
        return False, f"No Manifest"

    def new_arg(value, pre = '', post = ''):
        if not value:
            return {'pre': '', 'value': '' , 'post': '', 'full': ''}
        return {
            'pre': pre,
            'value': escape_input(value),
            'post': post,
            'full': f"{pre}{value}{post}"
        }
    args = {}


    awg_outputs = ['oneshot_rearm', 'oneshot', 'continuous']
    if output in awg_outputs:
        if not segment:
            return False, f"Segment is required" #possibly temp
        args['output'] = new_arg(output, '--awg_mode ')

    else:
        globals.last_file = f"{escape_input(output)}.dat"
        args['output'] = new_arg(output, '-o /tmp/', '.dat')

    args['nreps'] = new_arg(nreps, '--nreps ')
    args['segment'] = new_arg(segment, '--abcde ')
    args['pattern'] = new_arg(pattern)

    globals.last_compose = args
    cmd = f"/usr/local/bin/awg_composer {' '.join([value.get('full') for key, value in args.items()])}"
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
    response.body = json.dumps({'compose_status': globals.compose_status})
    response.content_type = 'application/json'
    return response

def handle_compose_download(response, api):
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

def handle_last_compose(response, api):
    response.status = 200
    response.body = json.dumps(globals.last_compose)
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
    try:
        out = subprocess.run(cmd, shell=True, timeout=30)
    except Exception as e:
        globals.compose_status[1] = f"Errored {e}"
    else:
        print(out)
        if out.returncode == 0:
            globals.compose_status[1] = f"Done {round(time.time() - start_time, 2)}s"
        else:
            globals.compose_status[1] = f"Returned with error"
    finally:
        globals.compose_status[0] = False
    print(f"[COMPOSER] Finished")


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
        'compose_last' : handle_last_compose,
    },
}