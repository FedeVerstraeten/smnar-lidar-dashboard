const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const elements = new Map();
function $(selector) {
  if (typeof selector === 'function') { return; }
  const names = selector.split(',').map(name => name.trim());
  names.forEach(name => { if (!elements.has(name)) { elements.set(name, {}); } });
  const api = {};
  ['prop', 'text', 'val'].forEach(method => {
    api[method] = function (key, value) {
      if (method === 'prop') {
        if (arguments.length === 1) { return elements.get(names[0])[key]; }
        names.forEach(name => { elements.get(name)[key] = value; });
      } else {
        if (!arguments.length) { return elements.get(names[0])[method] || ''; }
        names.forEach(name => { elements.get(name)[method] = key; });
      }
      return api;
    };
  });
  ['toggleClass', 'removeClass', 'addClass', 'on'].forEach(method => { api[method] = () => api; });
  return api;
}

const context = {window: {}, document: {hidden: false}, $, setTimeout() {}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/js/motorcontrols.js'), 'utf8'), context);
const disabled = name => elements.get(name).disabled;

context.setMotorConnectionStatus({connected: false, busy: false, port: 'COM4'});
assert.equal(disabled('#motor_left_btn'), true);
assert.equal(disabled('#autoalign_start_btn'), true);
assert.equal(disabled('[data-motion-action]'), true);
assert.equal(disabled('#motor_connectbtn'), false);

context.setMotorConnectionStatus({connected: true, busy: false, port: 'COM4'});
assert.equal(disabled('#motor_left_btn'), false);
assert.equal(disabled('#autoalign_start_btn'), false);
assert.equal(disabled('[data-motion-action]'), false);
assert.equal(elements.get('#motor_port_input').readonly, true);

context.setMotorConnectionStatus({connected: true, busy: true, owner: 'telecover', port: 'COM4'});
assert.equal(disabled('#motor_left_btn'), true);
assert.equal(disabled('#autoalign_start_btn'), true);
assert.equal(disabled('#motor_disconnectbtn'), true);
assert.equal(disabled('[data-motion-stop]'), false);

context.window.autoalignmentState = {running: true, moving: false};
context.setMotorConnectionStatus({connected: true, busy: false, port: 'COM4'});
assert.equal(disabled('#motor_left_btn'), true);
assert.equal(disabled('#autoalign_start_btn'), true);

context.window.autoalignmentState = {running: false, moving: false, status: 'Complete', best: {pearson: 0.9}};
context.updateMotorActionButtons();
assert.equal(disabled('#autoalign_move_best_btn'), false);
context.setMotorConnectionStatus({motor_connection: {connected: false, busy: false, port: 'COM4', ok: false, message: 'USB lost'}});
assert.equal(disabled('#autoalign_move_best_btn'), true);
assert.equal(disabled('[data-motion-stop]'), true);
assert.equal(elements.get('#motor_connection_status').text, 'USB lost');

console.log('Motor UI: connection, busy, scan, stop and disconnect states verified.');
