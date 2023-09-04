#!/usr/bin/env python3

import argparse
import os
import importlib
import json

from bottle import Bottle, response, request

# WEBSERVER
def enable_cors(fn):
    def _enable_cors(*args, **kwargs):
        global request
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
        if request.method != 'OPTIONS':
            return fn(*args, **kwargs)
        return response
    return _enable_cors

def root_handler():
    response.content_type = 'text/plain'
    response.status = 200
    return 'root_handler'

@enable_cors
def endpoint_handler():
    global response

    #default = lambda o: f"<<non-serializable: {type(o).__qualname__}>>"
    #print(f"[endpoint_handler] POST")
    #print(json.dumps(request.json, indent=2, default=default))

    def error_json(msg):
        error = {
            'error': True,
            'msg' : type(msg).__name__,
        }
        return error

    try:
        action = api.actions[request.json['action']]
        data = request.json['data']
        try:
            result, body = action(**data)
            status = 200 if result else 400
        except Exception as e:
            print(e)
            body = error_json(e)
            status = 400
    except Exception as e:
            print(e)
            body = error_json('Invalid json')
            status = 400

    response.status = status        
    response.content_type = 'application/json'
    return body

@enable_cors
def state_handler(state):
    global response
    global request
    client_ip = request.environ.get('REMOTE_ADDR')
    print(f"[state_handler] {client_ip} GET {state}")

    try:
        response = api.states[state](response, api)
    except Exception as e:
        print('[state_handler] ERROR')
        print(e)
        response.status = 404
        response.body = '404 Page not found'

    return response

class api:
    actions = {}
    states = {}
    html = {}

    routes = {
        '/' : {
            'method' : ['GET'],
            'handler' : root_handler
        },
        '/endpoint' : {
            'method' : ['POST', 'OPTIONS'],
            'handler' : endpoint_handler
        },
        '/<state>' : {
            'method' : ['GET'],
            'handler' : state_handler
        },
    }

    def add_actions(actions):
        for action, handler in actions.items():
            print(f"[add_actions] Adding {action} {handler}")
            api.actions[action] = handler

    def add_states(states):
        for states, handler in states.items():
            print(f"[add_states] Adding {states} {handler}")
            api.states[states] = handler

    def add_html(name, filename):
        api.html[name] = filename

    def setup_routing(app):
        for route, config in api.routes.items():
            print(f"[setup_routing] Adding route {config['method']} {route}")
            app.route(route, config['method'], config['handler']) 

#filesystem setup
def init_dirs():
    api.root_dir = os.path.dirname(os.path.realpath(__file__))
    api.endpoints_dir = os.path.join(api.root_dir, 'endpoints')
    api.res_dir = os.path.join(api.root_dir, 'resources')
    api.web_dir = os.path.join(api.root_dir, 'www')

def import_endpoints(endpoints):
    for endpoint in endpoints:
        filepath = os.path.join(api.endpoints_dir, f"{endpoint}.py")
        if not os.path.isfile(filepath):
            print(f"[import_endpoints] {endpoint} not found ignoring")
            continue
        print(f"[import_endpoints] NEW endpoint {endpoint}")
        module = importlib.import_module(f"endpoints.{endpoint}")
        if 'actions' in module.manifest:
            api.add_actions(module.manifest['actions'])
        if 'states' in module.manifest:
            api.add_states(module.manifest['states'])
        if 'html' in module.manifest:
            api.add_html(module.manifest['name'], module.manifest['html'])

def init_html():
    if not os.path.isdir(api.web_dir):
        os.mkdir(api.web_dir)
    for file in os.listdir(api.web_dir):
        print(f"[init_html] disabling {file}")
        os.unlink(os.path.join(api.web_dir, file))
    os.symlink(os.path.join(api.res_dir, 'static'), os.path.join(api.web_dir, 'static'))
    print(f"[init_html] enabling static/")
    for name, filename in api.html.items():
        filepath = os.path.join(api.res_dir, filename)
        destination = os.path.join(api.web_dir,  filename)
        print(f"[init_html] enabling {filename}")
        os.symlink(filepath, destination)
    if not os.path.islink('/var/www/apps'):
        print(f"[init_html] enabling /var/www/apps")
        os.symlink(api.web_dir, '/var/www/apps')

def generate_config(port):
    lines = [
        f"const PORT = {port};",
        f"const HOST = '{os.uname().nodename}';"
    ]
    with open(os.path.join(api.web_dir, 'config.js'), 'w') as file:
        file.writelines(lines)

def hijack_nginx():
    root_index = '/var/www/d-tacq/acq_main_page.html'
    apps_index = '/var/www/apps/index.html'
    new_tab = '<li><a title="Apps" href="/apps">Apps</a></li>'
    print('[hijack_nginx] Greping')
    rtnval = os.system(f"grep '{new_tab}' {root_index}")
    if rtnval > 0:
        print('[hijack_nginx] Inserting new Tab')
        os.system(f"sed -i '/^<!-- TABAPPEND -->.*/a {new_tab}' {root_index}")
    list_items = ''
    print(api.html)
    for title, file in api.html.items():
        list_items += f"<li><a href='/apps/{file}'>{title}</a></li>"
    index_html = f"""
        <h1>Apps</h1>
        <ul>
            {list_items}
        </ul>
    """
    with open(apps_index, 'w') as f:
        f.write(index_html)
    print('[hijack_nginx] Done')


#starts here
def run_main(args):
    print('Starting')
    if len(args.endpoints) == 0:
        print('Error: no valid endpoints')
        exit(1)
    init_dirs()
    import_endpoints(args.endpoints)
    init_html()
    generate_config(args.web_port)
    hijack_nginx()

    app = Bottle()
    api.setup_routing(app)
    app.run(host='0.0.0.0', port=args.web_port, quiet=args.quiet)

def list_of_strings(string):
    return string.split(',')

def get_parser():
    parser = argparse.ArgumentParser(description='awg_composer_web')
    parser.add_argument('--web_port', default=5001, help="webserver port")
    parser.add_argument('--quiet', default=True, help="webserver hush")
    parser.add_argument('endpoints', nargs='*', default=[], help="Endpoints to enable")
    return parser

if __name__ == "__main__":
    run_main(get_parser().parse_args())