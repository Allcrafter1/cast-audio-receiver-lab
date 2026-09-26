// Browser regression tests use only synthetic routes; no receiver is contacted.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const assets = path.join(__dirname, '../src/cast_audio_lab/web');
const routes = [
  {id:'local', name:'Wohnzimmer', backend:'mpv', enabled:false, process:{state:'disabled', restarts:0}},
  {id:'dlna', name:'Living room', backend:'dlna', enabled:true, target:{host:'192.0.2.20', port:80, protocol:'dlna', description_url:'http://192.0.2.20/device.xml'}, process:{state:'running', restarts:2}},
  {id:'sonos', name:'Sonos', backend:'sonos', enabled:false, process:{state:'backoff', restarts:3}},
];
const candidate = {name:'Discovered speaker', candidate_id:'candidate', already_imported:false, target:{host:'192.0.2.30', port:7000, protocol:'raop'}};
async function fixture(browser, locale, base, storageBlocked = false, mobile = false) {
  const context = await browser.newContext({locale, viewport: mobile ? {width:375,height:812} : {width:1280,height:1000}});
  if (storageBlocked) await context.addInitScript(() => Object.defineProperty(window, 'localStorage', {get() {throw new Error('blocked');}}));
  const page = await context.newPage();
  const errors = [], writes = [];
  let failure = null, finishScan;
  page.on('pageerror', error => errors.push(error.message));
  await page.route('http://receiver.test/**', async route => {
    const request = route.request(), url = new URL(request.url());
    assert.ok(url.pathname.startsWith(base), 'requests must retain the ingress prefix');
    const relative = url.pathname.slice(base.length);
    if (relative.startsWith('api/')) {
      if (request.method() !== 'GET') writes.push({url: relative, body: request.postDataJSON()});
      if (relative === 'api/scan' || relative === 'api/scan/dlna') {
        await new Promise(resolve => { finishScan = resolve; });
        return route.fulfill({json:{candidates:[candidate]}});
      }
      if (failure) return route.fulfill({status:failure.status, json:{error:failure.error}});
      return route.fulfill({json:{routes,version:'test'}});
    }
    const name = relative || 'index.html';
    assert.ok(['index.html','app.js','style.css','favicon.svg'].includes(name));
    return route.fulfill({body:fs.readFileSync(path.join(assets, name)), contentType: {'index.html':'text/html','app.js':'text/javascript','style.css':'text/css','favicon.svg':'image/svg+xml'}[name]});
  });
  await page.goto('http://receiver.test' + base);
  await page.locator('#routes .route').nth(2).waitFor();
  return {page, context, errors, writes, fail: value => {failure=value;}, finish: () => finishScan()};
}
const select = (page, lang) => page.locator(`[data-language="${lang}"]`).click();
async function checkLanguage(page, lang) {
  assert.equal(await page.locator('html').getAttribute('lang'), lang);
  assert.equal(await page.locator(`[data-language="${lang}"]`).getAttribute('aria-pressed'), 'true');
  assert.equal(await page.locator('h1').textContent(), lang === 'de' ? 'Deine Speaker.' : 'Your speakers.');
  assert.equal(await page.locator('#routes .route').first().locator('button').first().textContent(), lang === 'de' ? 'Name speichern' : 'Save name');
  assert.match(await page.locator('#routes .state').nth(1).textContent(), lang === 'de' ? /Prozess läuft · Neustarts: 2/ : /Process running · Restarts: 2/);
  const untranslated = await page.evaluate(() => {
    const missing = [];
    for (const key of Object.keys(translations.en)) {
      if (!Object.hasOwn(translations.de, key)) missing.push(key);
      const slots = value => (value.match(/\{\w+\}/g) || []).sort().join(',');
      if (slots(translations.en[key]) !== slots(translations.de[key])) missing.push(key + ': placeholders');
    }
    for (const n of document.querySelectorAll('[data-i18n], [data-i18n-aria]')) {
      const key = n.dataset.i18n || n.dataset.i18nAria;
      if (!Object.hasOwn(translations.en, key) || !Object.hasOwn(translations.de, key)) missing.push(key);
    }
    return missing;
  });
  assert.deepEqual(untranslated, []);
}
(async () => {
  const browser = await chromium.launch({headless:true, args:['--no-sandbox']});
  try {
    for (const base of ['/', '/api/hassio_ingress/test-session/']) {
      const f = await fixture(browser, 'de-DE', base);
      const {page} = f;
      await checkLanguage(page, 'de');
      assert.equal(await page.locator('#add-local').isDisabled(), true);
      await page.locator('#routes input').first().fill('Unsaved <speaker>');
      await page.locator('[data-i18n-aria="dlna_url_label"]').fill('http://192.0.2.99/draft.xml');
      await page.locator('#sonos-name').fill('Mein Sonos');
      await select(page, 'en');
      await checkLanguage(page, 'en');
      assert.equal(await page.locator('#routes input').first().inputValue(), 'Unsaved <speaker>');
      assert.equal(await page.locator('[data-i18n-aria="dlna_url_label"]').inputValue(), 'http://192.0.2.99/draft.xml');
      assert.equal(await page.locator('#sonos-name').inputValue(), 'Mein Sonos');
      assert.equal(await page.locator('#add-local').isDisabled(), true);
      assert.deepEqual(f.writes, [], 'language switch must not write configuration');
      await page.locator('#scan').click();
      await page.waitForFunction(() => document.getElementById('message').textContent.includes('Searching'));
      await select(page, 'de');
      assert.match(await page.locator('#message').textContent(), /Suche AirPlay/);
      assert.equal(await page.locator('#scan').isDisabled(), true);
      f.finish();
      await page.locator('#candidates input').waitFor();
      await page.locator('#candidates input').fill('Draft target');
      await select(page, 'en');
      assert.equal(await page.locator('#candidates input').inputValue(), 'Draft target');
      assert.match(await page.locator('#message').textContent(), /1 endpoints found/);
      assert.equal(await page.locator('#candidates button').textContent(), 'Import disabled');
      for (const lang of ['en','de']) {
        await select(page, lang);
        const dialog = page.waitForEvent('dialog');
        const click = page.locator('#routes .route').first().getByRole('button', {name:lang === 'de' ? 'Löschen' : 'Delete', exact:true}).click();
        const confirmation = await dialog;
        assert.match(confirmation.message(), lang === 'de' ? /löschen/ : /Delete speaker/);
        await confirmation.dismiss(); await click;
      }
      f.fail({status:409,error:'Discovery expired; scan again'});
      await page.locator('#refresh').click();
      await page.waitForFunction(() => document.getElementById('message').textContent.includes('abgelaufen'));
      await select(page, 'en');
      assert.match(await page.locator('#message').textContent(), /Discovery expired/);
      f.fail({status:403,error:'forbidden'});
      await page.locator('#refresh').click();
      await page.waitForFunction(() => document.getElementById('message').textContent.includes('Home Assistant'));
      assert.match(await page.locator('#message').textContent(), /Access failed/);
      f.fail(null);
      await page.reload(); await page.locator('#routes .route').nth(2).waitFor();
      await checkLanguage(page, 'en'); // Stored choice wins over German browser.
      assert.deepEqual(f.errors, []);
      assert.equal(f.writes.length, 1); // Only the deliberate discovery request.
      if (process.env.UI_SCREENSHOTS && base === '/') {
        fs.mkdirSync(process.env.UI_SCREENSHOTS, {recursive:true});
        await page.screenshot({path:path.join(process.env.UI_SCREENSHOTS,'english-desktop.png'),fullPage:true});
      }
      await f.context.close();
    }
    const mobile = await fixture(browser, 'fr-FR', '/', true, true);
    await checkLanguage(mobile.page, 'en'); // Unsupported browser language falls back to English.
    for (const lang of ['de','en']) {
      await select(mobile.page, lang); await checkLanguage(mobile.page, lang);
      assert.ok(await mobile.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      const box = await mobile.page.locator('.language-switch').boundingBox();
      assert.ok(box.x >= 0 && box.x + box.width <= 375 && box.y < 150);
    }
    await select(mobile.page, 'de');
    if (process.env.UI_SCREENSHOTS) await mobile.page.screenshot({path:path.join(process.env.UI_SCREENSHOTS,'german-mobile.png'),fullPage:true});
    assert.deepEqual(mobile.errors, []);
    await mobile.context.close();
    console.log('PASS: DE/EN, persistence, blocked storage, mobile, ingress, drafts, discovery, confirmations and errors');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode=1;});
