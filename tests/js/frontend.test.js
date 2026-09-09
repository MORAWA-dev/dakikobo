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
            headers: { 'Content-Type': 'application/json', 'X-DakiKobo-Cacheable':'1', 'X-DakiKobo-Corpus':'test-corpus', 'X-DakiKobo-Saved-At':String(Date.now()/1000) }
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

function loadServiceWorker(fertilizerTable, fetchImpl, clock) {
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
                keys: async function() { return Array.from(entries.keys()).map(function(url) { return new Request(url); }); },
                delete: async function(request) { return entries.delete(absoluteUrl(request)); },
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
        Date: clock || Date,
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
        false
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
    assert.equal(payload.case, undefined);
    assert.equal(payload.confidence, 'Faible');
    assert.match(payload.answer, /petit mil|le mil/);
    assert.doesNotMatch(payload.answer, /\d+\s*(kg|g)\b/i);

    const groundnut = new FormData();
    groundnut.append('messageText', "Quelle fumure pour la cacahuète ?");
    groundnut.append('crop', '');
    const groundnutPayload = await (await worker.offlineFertilizer(groundnut)).json();
    assert.equal(groundnutPayload.case, undefined);
    assert.match(groundnutPayload.answer, /arachide/);
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
                headers: { 'Content-Type': 'application/json', 'X-DakiKobo-Cacheable':'1', 'X-DakiKobo-Corpus':'test-corpus', 'X-DakiKobo-Saved-At':String(Date.now()/1000) }
            });
        }
        return new Response('ressource externe');
    });

    let installPromise;
    runtime.handlers.install({ waitUntil: function(promise) { installPromise = promise; } });
    await installPromise;
    const shell = Array.from(runtime.buckets.entries()).find(function(entry) { return entry[0].endsWith('-shell'); })[1];
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

test('la culture explicite prime sur une ancienne sélection hors ligne', async function() {
    const { worker } = loadServiceWorker(require('../../static/data/fertilizer.json'));
    const form = new FormData();
    form.set('crop', 'sorgho');
    form.set('messageText', 'Quel engrais pour le maïs ?');
    const payload = await (await worker.offlineFertilizer(form)).json();
    assert.match(payload.answer, /maïs/);
    assert.doesNotMatch(payload.answer, /sorgho/);
    assert.equal(payload.answer_kind, 'refusal');
});

test('hors ligne demande une clarification pour une culture ambiguë ou non prise en charge', async function() {
    const { worker } = loadServiceWorker(require('../../static/data/fertilizer.json'));
    const cases = [
        ['Engrais pour le soja ?', /pas disponible/],
        ['Engrais pour le mil et le maïs ?', /plusieurs cultures/]
    ];
    for (const [question, expected] of cases) {
        const form = new FormData(); form.set('crop','sorgho'); form.set('messageText',question);
        const response = await worker.offlineFertilizer(form);
        const payload = await response.json();
        assert.equal(response.status, 200);
        assert.equal(payload.clarification_required, true);
        assert.match(payload.answer, expected);
        assert.equal(payload.case, undefined);
    }
});

test("hors ligne demande la culture d'un suivi sans contexte sûr", async function() {
    const { worker } = loadServiceWorker(require('../../static/data/fertilizer.json'));
    const form = new FormData();
    form.set('crop', 'sorgho');
    form.set('prior_question', 'Quel engrais pour le maïs ?');
    form.set('messageText', 'Quel engrais utiliser ?');
    const payload = await (await worker.offlineFertilizer(form)).json();
    assert.equal(payload.clarification_required, true);
    assert.match(payload.answer, /précisez la culture/);
    assert.equal(payload.case, undefined);
});

test("une installation hors ligne incomplète refuse sans planter", async function() {
    const { worker } = loadServiceWorker(null);
    const form = new FormData();
    form.set('crop', 'sorgho');
    form.set('messageText', 'Quel engrais utiliser ?');
    assert.equal(await worker.offlineFertilizer(form), null);
});

test('les réponses expirées et la météo ne sont pas rejouées', async function() {
    let now = Date.now();
    let online = true;
    class Clock extends Date { static now() { return now; } }
    const runtime = loadServiceWorker(require('../../static/data/fertilizer.json'), async function() {
        if (!online) { throw new Error('offline'); }
        return new Response(JSON.stringify({answer:'Ancien conseil météo'}), { headers: {
            'X-DakiKobo-Cacheable':'1', 'X-DakiKobo-Corpus':'v1', 'X-DakiKobo-Saved-At':String(now/1000)
        }});
    }, Clock);
    function request() {
        const form = new FormData(); form.set('messageText','Quand semer ?');
        return new runtime.Request('/ask', {method:'POST',body:form});
    }
    await runtime.worker.networkFirstAsk(request());
    online = false; now += 25*3600*1000;
    assert.equal((await runtime.worker.networkFirstAsk(request())).status, 503);
});

test('une nouvelle version du corpus invalide les anciennes réponses', async function() {
    let corpus = 'v1'; let online = true;
    const runtime = loadServiceWorker(require('../../static/data/fertilizer.json'), async function() {
        if (!online) { throw new Error('offline'); }
        return new Response(JSON.stringify({answer:'Conseil'}), {headers:{'X-DakiKobo-Cacheable':'1','X-DakiKobo-Corpus':corpus,'X-DakiKobo-Saved-At':String(Date.now()/1000)}});
    });
    function request(text) { const form = new FormData(); form.set('messageText',text); return new runtime.Request('/ask',{method:'POST',body:form}); }
    await runtime.worker.networkFirstAsk(request('Question un'));
    corpus = 'v2'; await runtime.worker.networkFirstAsk(request('Question deux'));
    online = false;
    assert.equal((await runtime.worker.networkFirstAsk(request('Question un'))).status,503);
    assert.equal((await runtime.worker.networkFirstAsk(request('Question deux'))).status,200);
});

test('clearDeviceData conserve les autres applications', async function() {
    const storage = {dakikobo_field_context_v1:'private', other_app:'keep'};
    storage.removeItem = function(key) { delete storage[key]; };
    global.localStorage = storage;
    const deleted = [];
    global.caches = {keys:async()=>['dakikobo-v1-answers','dakikobo-v1-shell','other'],delete:async(key)=>deleted.push(key)};
    await api.clearDeviceData();
    assert.equal(storage.dakikobo_field_context_v1,undefined);
    assert.equal(storage.other_app,'keep');
    assert.deepEqual(deleted,['dakikobo-v1-answers']);
    delete global.localStorage; delete global.caches;
});



test("une nouvelle révision de sécurité invalide les réponses enregistrées", async function() {
    // Audit finding 3: a code-only safety deployment changes no document, so the
    // corpus marker alone left older answers replayable offline.
    let safety = 'safety-a.111111111111';
    let online = true;
    const runtime = loadServiceWorker(require('../../static/data/fertilizer.json'), async function() {
        if (!online) { throw new Error('offline'); }
        return new Response(JSON.stringify({ answer: 'Conseil enregistré' }), {
            headers: {
                'X-DakiKobo-Cacheable': '1',
                'X-DakiKobo-Corpus': 'corpus-stable',
                'X-DakiKobo-Safety': safety,
                'X-DakiKobo-Saved-At': String(Date.now() / 1000)
            }
        });
    });
    function request(text) {
        const form = new FormData();
        form.set('messageText', text);
        return new runtime.Request('/ask', { method: 'POST', body: form });
    }

    await runtime.worker.networkFirstAsk(request('Question un'));

    // Same corpus, stricter safety policy.
    safety = 'safety-b.222222222222';
    await runtime.worker.networkFirstAsk(request('Question deux'));

    online = false;
    const stale = await runtime.worker.networkFirstAsk(request('Question un'));
    assert.equal(stale.status, 503, "une réponse d'avant la révision a été rejouée");
    const fresh = await runtime.worker.networkFirstAsk(request('Question deux'));
    assert.equal(fresh.status, 200);
    assert.equal((await fresh.json()).answer, 'Conseil enregistré');
});

test('les marqueurs de cache ne consomment pas le quota de réponses', async function() {
    const runtime = loadServiceWorker(require('../../static/data/fertilizer.json'), async function() {
        return new Response(JSON.stringify({ answer: 'Conseil' }), {
            headers: {
                'X-DakiKobo-Cacheable': '1',
                'X-DakiKobo-Corpus': 'corpus-stable',
                'X-DakiKobo-Safety': 'safety-a.111111111111',
                'X-DakiKobo-Saved-At': String(Date.now() / 1000)
            }
        });
    });
    function request(text) {
        const form = new FormData();
        form.set('messageText', text);
        return new runtime.Request('/ask', { method: 'POST', body: form });
    }

    for (let index = 0; index < 4; index += 1) {
        await runtime.worker.networkFirstAsk(request('Question ' + index));
    }

    const answers = Array.from(runtime.buckets.entries())
        .find(function(entry) { return entry[0].endsWith('-answers'); })[1];
    const paths = Array.from(answers.entries.keys()).map(function(url) { return new URL(url).pathname; });
    // Both identity markers persist alongside the four saved answers.
    assert.ok(paths.indexOf('/__corpus__') !== -1);
    assert.ok(paths.indexOf('/__safety__') !== -1);
    assert.equal(paths.filter(function(p) { return p.indexOf('/__dakikobo_answer__') === 0; }).length, 4);
});
