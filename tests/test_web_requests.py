"""Execute the browser request helper, including HA's session cookie policy."""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node.js is needed for browser-helper tests")
class WebRequestTests(unittest.TestCase):
    def test_ingress_and_direct_requests(self):
        script = Path(__file__).parents[1] / "src/cast_audio_lab/web/app.js"
        result = subprocess.run(["node", "-e", r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
(async () => {
  const context = vm.createContext({
    document: {getElementById: () => ({})},
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
