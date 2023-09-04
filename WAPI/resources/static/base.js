//Common functions
console.log('common.js Loaded')

function download_file(uri, name) {
    var link = document.createElement("a");
    link.download = name;
    link.href = uri;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    delete link;
}
function send_request(url, method, callback, payload = null){
    var xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    xhr.onreadystatechange = function() {
        if(xhr.readyState == 4) {
            callback(xhr.status, xhr.response);
        }
    }
    if(payload){
        xhr.setRequestHeader('Content-Type', 'application/json');
    }
    xhr.send(payload);
}
function get_timestamp(){
    d = new Date();
    return `${d.getFullYear()}${d.getMonth() + 1}${d.getDate()}${d.getHours()}${d.getMinutes()}`
}
function init_event_listeners(map){
    for (const [selector, [events, funcs]] of Object.entries(map)) {
        document.querySelectorAll(selector).forEach((elem) => {
            for (let event of events) {
                for (let func of funcs) {
                    elem.addEventListener(event, (e) => {
                        func(e, e.target);
                    }, false);
                }
            }
        });
    }
}
function live_input_handler(e, elem){
    value = elem.value
    target = document.querySelector(elem.getAttribute('target'));
    if(elem.tagName == 'SELECT'){
        elem = elem.options[elem.selectedIndex]
    }
    elem.hasAttribute('editable') ? target.setAttribute('contenteditable', true) : target.setAttribute('contenteditable', false);
    target.innerText = value;
    if(elem.hasAttribute('pre')){
        target.setAttribute('pre', value ? elem.getAttribute('pre') : '')
    }
    if(elem.hasAttribute('post')){
        target.setAttribute('post', value ? elem.getAttribute('post') : '')
    }
}
