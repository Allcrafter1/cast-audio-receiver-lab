# SPDX-License-Identifier: MPL-2.0
"""Execute the browser request helper, including HA's session cookie policy."""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node.js is needed for browser-helper tests")
class WebRequestTests(unittest.TestCase):
    def test_late_refresh_and_poll_cannot_replace_newer_configuration(self):
        script = Path(__file__).parents[1] / "src/cast_audio_lab/web/app.js"
        result = subprocess.run(["node", "-e", r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
(async () => {
  const requests = [], seen = [];
  let poll;
  const context = vm.createContext({
    document: {getElementById: () => ({contains: () => false}), querySelectorAll: () => [],
      querySelector: () => null, documentElement: {}},
    navigator: {language: 'en'}, seen,
    fetch: () => new Promise(resolve => requests.push(resolve)),
    setInterval: callback => { poll = callback; },
  });
  vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
  vm.runInContext('renderRoutes = data => { seen.push(data.routes[0].name); renderedConfig = configKey(data.routes); }', context);
  const reply = (index, name) => requests[index]({ok: true, json: async () => ({routes: [{id:'a', name}]})});
  const older = vm.runInContext('refresh()', context);
  const newer = vm.runInContext('refresh()', context);
  reply(2, 'new'); await newer;
  reply(1, 'old'); await older;
  assert.deepEqual(seen, ['new'], 'late refresh overwrote the newer selection');
  const pendingPoll = poll();
  const afterSave = vm.runInContext('refresh()', context);
  reply(4, 'saved'); await afterSave;
  reply(3, 'before-save'); await pendingPoll;
  assert.deepEqual(seen, ['new', 'saved'], 'late poll undid the visible saved configuration');
})().catch(error => { console.error(error); process.exitCode = 1; });
''', str(script)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ingress_and_direct_requests(self):
        script = Path(__file__).parents[1] / "src/cast_audio_lab/web/app.js"
        result = subprocess.run(["node", "-e", r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
(async () => {
  const context = vm.createContext({
    document: {getElementById: () => ({}), querySelectorAll: () => [], documentElement: {}},
    navigator: {language: 'en'},
    fetch: () => new Promise(() => {}), setInterval: () => {},
  });
  vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
  let request;
  context.fetch = async (path, options) => {
    request = {path, options};
    return {ok: true, status: 200, json: async () => ({version: 'test'})};
  };
  await vm.runInContext('api("/api/routes")', context);
  assert.equal(request.path, 'api/routes');
  assert.equal(request.options.credentials, 'same-origin');
  assert.equal(request.options.cache, 'no-store');
  for (const base of ['http://receiver:8788/', 'https://ha.example/api/hassio_ingress/session/']) {
    assert.equal(new URL(request.path, base).href, base + 'api/routes');
  }
  context.fetch = async () => ({ok: false, status: 401});
  await assert.rejects(vm.runInContext('api("/api/routes")', context), /Home Assistant/);
})().catch(error => { console.error(error); process.exitCode = 1; });
''', str(script)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
