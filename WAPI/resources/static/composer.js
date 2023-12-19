console.log('composer.js Loaded');

const url_base = new URL(window.location.pathname, window.location.origin);
const api_url = new URL(`http://${HOST}:${PORT}`);
console.log(`Api url: ${api_url.toString()}`);

function upload_lines(e){
    const NEWLINE = '\n';
    file = e.target.files[0];
    const reader = new FileReader();
    reader.addEventListener("load", () => {
        let payload = {
            'action' : 'build_template',
            'data': {
                'lines' : reader.result.split(NEWLINE)
            }
        }
        let url = new URL(`${api_url.toString()}endpoint`);
        console.log(`[upload_lines] ${url.toString()}`)
        send_request(url.toString(), 'POST', (code, response) => {
            e.target.value = null;
            if(code >= 200 && code < 300){
                update_manifest();
                console.log('upload_lines succeded');
                return;
            }
            console.log('upload_lines failed');
            if(code == 0){
                response = 'Offline';
            }
            alert(response);
        }, JSON.stringify(payload));
    });
    if(file.type != 'text/plain'){
        alert(`Invalid filetype`);
        return;
    }
    reader.readAsText(file);
}
function update_manifest(){
    let url = new URL(`${api_url.toString()}manifest`);
    var manifest_contents = document.querySelector('#manifest-block');
    console.log(`[update_manifest] ${url.toString()}`)
    send_request(url.toString(), 'GET', function (code, response){
        manifest_contents.innerText = response;
        manifest_contents.classList = 'code_block';
        manifest_contents.offsetWidth;
        if(code < 200 || code > 399){
            manifest_contents.innerText = 'None';
            manifest_contents.classList = 'code_block animate_update';
            return;
        }
        manifest_contents.classList = 'code_block animate_update has_manifest';
    });
}
function erase_mainfest(e){
    let payload = {
        'action' : 'erase_mainfest',
        'data' : {}
    }
    let url = new URL(`${api_url.toString()}endpoint`);
    console.log(`[erase_templates] ${url.toString()}`)
    send_request(url.toString(), 'POST', (code, response) => {
        update_manifest();
    }, JSON.stringify(payload));
}
function start_compose(e){
    console.log(`[start_compose]`)

    compose_status = document.querySelector('#compose-status');
    output = document.querySelector('#compose-output .value').innerText;
    pattern = document.querySelector('#compose-pattern .value').innerText;
    nreps = document.querySelector('#compose-nreps .value').innerText;
    segment = document.querySelector('#compose-segment .value').innerText;

    function poll_until_complete(){
        let url = new URL(`${api_url.toString()}compose_status`);
        compose_status.classList = '';
        console.log(`[poll_until_complete] ${url.toString()}`)
        send_request(url.toString(), 'GET', function (code, response){
            var [composing, status] = JSON.parse(response)['compose_status'];
            compose_status.innerText = status;
            compose_status.classList = 'animate_update';
            if(!composing){
                return
            }
            setTimeout(poll_until_complete, 1000); 
        });
    }
    let payload = {
        'action' : 'awg_compose',
        'data' : {
            'output' : output,
            'pattern' : pattern,
            'nreps' : nreps,
            'segment' : segment,
        }
    }
    console.log(payload)
    let url = new URL(`${api_url.toString()}endpoint`);
    send_request(url.toString(), 'POST', (code, response) => {
        if(code >= 200 && code < 300){
            poll_until_complete();
            return;
        }
        alert(response);
    }, JSON.stringify(payload));
}
function download_compose(){
    let url = new URL(`${api_url.toString()}compose_download`);
    console.log(`[download_compose] ${url.toString()}`);
    send_request(url.toString(), 'GET', function (code, response){
        if(code >= 200 && code < 300){
            response = JSON.parse(response);
            url = response['url'];
            filename = response['filename'];
            timestamp = get_timestamp();
            filename = `${timestamp}.${filename}`
            download_file(url, filename);
            return
        }
        error = JSON.parse(response)['error'];
        if (code == 0){
            error = 'Offline';
        }
        alert(error);
    });
}
var lpp_timeout = null
function lpp_update(e){
    value = e.target.value
    clearTimeout(lpp_timeout);
    if(!value){
        return
    }
    function send_lpp(rearm_num){
        compose_status = document.querySelector('#lpp-status');
        compose_status.classList = '';
        let payload = {
            'action' : 'lpp_rearm',
            'data' : {
                'rearm_num' : rearm_num
            }
        }
        let url = new URL(`${api_url.toString()}endpoint`);
        send_request(url.toString(), 'POST', (code, response) => {
            if(code >= 200 && code < 300){
                compose_status.classList = 'animate_update';
                compose_status.innerText = response;
                return;
            }
            alert(response);
        }, JSON.stringify(payload));
    }
    lpp_timeout = setTimeout(send_lpp, 700, value);
}
function trigger_soft_trigger(){
    console.log('trigger_soft_trigger')
    compose_status = document.querySelector('#lpp-status');
    compose_status.classList = '';
    let payload = {
        'action' : 'trigger_soft_trigger',
        'data' : {}
    }
    let url = new URL(`${api_url.toString()}endpoint`);
    send_request(url.toString(), 'POST', (code, response) => {
        if(code >= 200 && code < 300){
            compose_status.classList = 'animate_update';
            compose_status.innerText = response;
            return;
        }
        alert(response);
    }, JSON.stringify(payload));
}

function animate_drop_area(e){
    drop_area = document.querySelector('#drop-area');
    if(e.type == 'dragenter' || e.type == 'dragover'){
        drop_area.classList.add('active')
    }
    if(e.type == 'dragleave' || e.type == 'drop'){
        drop_area.classList.remove('active')
    }
    e.stopPropagation()
}

//Execution starts here
window.onload = ()=>{
    listener_map = {
        '.live_input': [['input'], [live_input_handler]],
        '#upload-input': [['change'], [upload_lines]],
        '#manifest-erase': [['click'], [erase_mainfest]],
        '#compose-start': [['click'], [start_compose]],
        '#compose-download': [['click'], [download_compose]],
        '#lpp-input': [['input'], [lpp_update]],
        '#soft-trigger': [['click'], [trigger_soft_trigger]],
        '#drop-area': [['dragenter', 'dragleave', 'dragover', 'drop'],[animate_drop_area]],
    }
    init_event_listeners(listener_map);

    function poll_manifest(){
        checkbox = document.querySelector('#manifest-refresh');
        if(checkbox.checked && document.visibilityState == 'visible'){
            update_manifest();
        }
        setTimeout(poll_manifest, 5000);
    }
    poll_manifest();
}
