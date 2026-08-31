'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const { JSDOM } = require('jsdom');

const renderFactory = require('../../static/js/render.js');
const api = require('../../static/js/api.js');

function fakeJquery() {
    return function() {
        return {
            0: { scrollHeight: 0 },
            scrollTop: function() { return this; }
        };
    };
}

test('cleanDisplayText ne contient pas de correspondance vide', function() {
    const dom = new JSDOM('<div class="chat-messages"></div>');
    global.document = dom.window.document;
    const render = renderFactory.create(fakeJquery());

    assert.equal(render.cleanDisplayText('Conseil agricole utile'), 'Conseil agricole utile');
    assert.equal(render.cleanDisplayText(''), '');
    assert.equal(
        render.cleanDisplayText('route commerciale avec vente de bois et marchés villageois dans une longue ligne à masquer'),
        ''
    );
});

test('typeMessage écrit uniquement du texte', async function() {
    const dom = new JSDOM('<div class="chat-messages"></div>');
    global.document = dom.window.document;
    const render = renderFactory.create(fakeJquery());
    let value = '';
    const element = {
        text: function(next) {
            if (next !== undefined) {
                value = next;
            }
            return value;
        }
    };

    await new Promise(function(resolve) {
        render.typeMessage('<img src=x onerror=alert(1)>', element, 0, resolve);
    });
    assert.equal(value, '<img src=x onerror=alert(1)>');
    assert.equal(dom.window.document.querySelector('img'), null);
});

test('uploadImageForScreening conserve ses six arguments', async function() {
    const originalFetch = global.fetch;
    let request;
    global.fetch = async function(url, options) {
        request = { url: url, options: options };
        return new Response(JSON.stringify({ answer: 'ok' }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
        });
    };
    try {
        assert.equal(api.uploadImageForScreening.length, 6);
        await api.uploadImageForScreening(
            new Blob(['photo'], { type: 'image/jpeg' }),
            'mais',
            'floraison',
            'Koudougou',
            true,
            'Photo maladie'
        );
        assert.equal(request.url, '/screen');
        assert.equal(request.options.body.get('question'), 'Photo maladie');
        assert.equal(request.options.body.get('simple_french'), '1');
    } finally {
        global.fetch = originalFetch;
    }
});

function loadServiceWorker(fertilizerTable, fetchImpl) {
    const handlers = {};
    const buckets = new Map();
    const externalFetches = [];
    const absoluteUrl = function(value) {
        const raw = typeof value === 'string' ? value : value.url;
        return new URL(raw, 'https://dakikobo.test').href;
    };
    const cacheFor = function(name) {
        if (!buckets.has(name)) {
            const entries = new Map();
            buckets.set(name, {
                entries: entries,
                addAll: async function(urls) {
                    urls.forEach(function(url) {
                        entries.set(absoluteUrl(url), new Response('précaché:' + url));
                    });
                },
                put: async function(request, response) {
                    entries.set(absoluteUrl(request), response.clone());
                },
                match: async function(request) {
                    const response = entries.get(absoluteUrl(request));
                    return response ? response.clone() : undefined;
                }
            });
        }
        return buckets.get(name);
    };
    const cacheStorage = {
        open: async function(name) { return cacheFor(name); },
        keys: async function() { return Array.from(buckets.keys()); },
        delete: async function(name) { return buckets.delete(name); },
        match: async function(request) {
            if (request === '/static/data/fertilizer.json') {
                return new Response(JSON.stringify(fertilizerTable));
            }
            for (const cache of buckets.values()) {
                const response = await cache.match(request);
                if (response) {
                    return response;
                }
            }
            return undefined;
        }
    };
    class ScopedRequest extends Request {
        constructor(input, options) {
            super(typeof input === 'string' ? absoluteUrl(input) : input, options);
        }
    }
    const workerFetch = fetchImpl || (async function(request) {
        externalFetches.push(absoluteUrl(request));
        return new Response('réseau');
    });
    const context = {
        URL,
        Request: ScopedRequest,
        Response,
        FormData,
        fetch: workerFetch,
        Promise,
        module: { exports: {} },
        caches: cacheStorage,
        self: {
            location: { origin: 'https://dakikobo.test' },
            addEventListener: function(name, handler) { handlers[name] = handler; },
            clients: { claim: async function() {} },
            skipWaiting: async function() {}
        }
    };
    const source = fs.readFileSync(path.join(__dirname, '../../static/sw.js'), 'utf8');
    vm.runInNewContext(source, context);
    return {
        Request: ScopedRequest,
        buckets: buckets,
        externalFetches: externalFetches,
        handlers: handlers,
        worker: context.module.exports
    };
}

test('le service worker ne met en cache que le shell explicite', function() {
    const table = require('../../static/data/fertilizer.json');
    const { worker } = loadServiceWorker(table);

    assert.equal(worker.shouldCacheFirst(new URL('https://dakikobo.test/registry')), true);
    assert.equal(worker.shouldCacheFirst(new URL('https://dakikobo.test/static/js/api.js')), true);
    assert.equal(worker.shouldCacheFirst(new URL('https://dakikobo.test/journal/due')), false);
    assert.equal(worker.shouldCacheFirst(new URL('https://dakikobo.test/weather?location=ouaga')), false);
    assert.equal(worker.shouldCacheFirst(new URL('https://dakikobo.test/healthz')), false);
    assert.equal(
        worker.shouldCacheFirst(new URL('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css')),
        true
    );
});

test('les alias canoniques fonctionnent pour la fumure hors ligne', async function() {
    const table = require('../../static/data/fertilizer.json');
    const { worker } = loadServiceWorker(table);
    const form = new FormData();
    form.append('messageText', "Quel engrais pour le petit mil ?");
    form.append('crop', '');

    const response = await worker.offlineFertilizer(form);
    const payload = await response.json();
    assert.equal(payload.case.crop, 'mil');
    assert.match(payload.answer, /100 kg\/ha de NPK/);

    const groundnut = new FormData();
    groundnut.append('messageText', "Quelle fumure pour la cacahuète ?");
    groundnut.append('crop', '');
    const groundnutPayload = await (await worker.offlineFertilizer(groundnut)).json();
    assert.equal(groundnutPayload.case.crop, 'arachide');
});

test('installation, navigation et réponses enregistrées fonctionnent sans réseau', async function() {
    const table = require('../../static/data/fertilizer.json');
    let online = true;
    const runtime = loadServiceWorker(table, async function(request) {
        const url = new URL(typeof request === 'string' ? request : request.url, 'https://dakikobo.test');
        if (url.pathname === '/ask') {
            if (!online) {
                throw new TypeError('réseau coupé');
            }
            return new Response(JSON.stringify({ answer: 'Réponse sourcée enregistrée', sources: [] }), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });
        }
        return new Response('ressource externe');
    });

    let installPromise;
    runtime.handlers.install({ waitUntil: function(promise) { installPromise = promise; } });
    await installPromise;
    const shell = runtime.buckets.get('dakikobo-phase5-v2-shell');
    assert.ok(shell.entries.has('https://dakikobo.test/'));
    assert.ok(shell.entries.has('https://dakikobo.test/registry'));
    assert.ok(shell.entries.has('https://dakikobo.test/static/data/fertilizer.json'));

    let navigationResponse;
    runtime.handlers.fetch({
        request: new runtime.Request('https://dakikobo.test/'),
        respondWith: function(promise) { navigationResponse = promise; }
    });
    assert.match(await (await navigationResponse).text(), /précaché:\//);

    const askRequest = function() {
        const form = new FormData();
        form.append('messageText', 'Quand semer le mil ?');
        form.append('crop', 'mil');
        return new runtime.Request('https://dakikobo.test/ask', { method: 'POST', body: form });
    };
    let onlineResponse;
    runtime.handlers.fetch({
        request: askRequest(),
        respondWith: function(promise) { onlineResponse = promise; }
    });
    assert.equal((await (await onlineResponse).json()).answer, 'Réponse sourcée enregistrée');
    await Promise.resolve();

    online = false;
    let offlineResponse;
    runtime.handlers.fetch({
        request: askRequest(),
        respondWith: function(promise) { offlineResponse = promise; }
    });
    const replay = await offlineResponse;
    assert.equal(replay.headers.get('X-DakiKobo-Offline'), '1');
    assert.equal((await replay.json()).answer, 'Réponse sourcée enregistrée');

    let journalIntercepted = false;
    runtime.handlers.fetch({
        request: new runtime.Request('https://dakikobo.test/journal/due'),
        respondWith: function() { journalIntercepted = true; }
    });
    assert.equal(journalIntercepted, false);
});
