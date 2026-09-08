'use strict';

var VERSION = 'dakikobo-farmer-v1-__ASSET_REVISION__';
var SHELL_CACHE = VERSION + '-shell';
var ANSWER_CACHE = VERSION + '-answers';
var ANSWER_MAX_AGE_MS = 24 * 60 * 60 * 1000;
var ANSWER_LIMIT = 50;
var SHELL = [
    '/',
    '/registry',
    '/crop-labels',
    '/static/manifest.webmanifest',
    '/static/css/style.css',
    '/static/js/render.js',
    '/static/js/api.js',
    '/static/js/index.js',
    '/static/vendor/jquery-3.6.0.min.js',
    '/static/images/logo.png',
    '/static/images/user_avatar.png',
    '/static/data/fertilizer.json',
    '/examples/semis_mil',
    '/examples/humidite_sorgho',
    '/examples/rotation_niebe',
    '/examples/oaph_burkina',
    '/examples/cilss_sahel',
    '/examples/hors_sujet',
    '/examples/fumure_sorgho',
    '/examples/photo_mais'
];
var EXTERNAL_SHELL = [];

self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(SHELL_CACHE)
            .then(function(cache) {
                return cache.addAll(SHELL).then(function() {
                    return Promise.all(EXTERNAL_SHELL.map(function(url) {
                        return fetch(url, { mode: 'no-cors' })
                            .then(function(response) { return cache.put(url, response); })
                            .catch(function() { return Promise.resolve(); });
                    }));
                });
            })
            .then(function() { return self.skipWaiting(); })
    );
});

self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(keys.map(function(key) {
                if (key.indexOf('dakikobo-') === 0 && key !== SHELL_CACHE && key !== ANSWER_CACHE) {
                    return caches.delete(key);
                }
                return Promise.resolve();
            }));
        }).then(function() { return self.clients.claim(); })
    );
});

function offlineJson(payload, status) {
    return new Response(JSON.stringify(payload), {
        status: status || 200,
        headers: {
            'Content-Type': 'application/json; charset=utf-8',
            'X-DakiKobo-Offline': '1'
        }
    });
}

function cacheFirst(request) {
    return caches.match(request).then(function(cached) {
        if (cached) {
            return cached;
        }
        return fetch(request).then(function(response) {
            if (response.ok) {
                caches.open(SHELL_CACHE).then(function(cache) { cache.put(request, response.clone()); });
            }
            return response;
        });
    });
}

function answerKey(formData) {
    var values = {};
    ['messageText', 'crop', 'growth_stage', 'location', 'simple_french', 'prior_question'].forEach(function(name) {
        values[name] = String(formData.get(name) || '').trim().toLowerCase();
    });
    return '/__dakikobo_answer__?q=' + encodeURIComponent(JSON.stringify(values));
}

function normalizeText(text) {
    return String(text || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .trim();
}

function containsTerm(text, term) {
    var escaped = normalizeText(term).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp('(^|[^a-z0-9])' + escaped + '([^a-z0-9]|$)').test(normalizeText(text));
}

function normalizeCrop(text, table) {
    var crops = table && table.crops ? table.crops : {};
    var cropIds = Object.keys(crops);
    for (var index = 0; index < cropIds.length; index += 1) {
        var cropId = cropIds[index];
        var aliases = [cropId].concat(crops[cropId].aliases || []);
        if (aliases.some(function(alias) { return containsTerm(text, alias); })) {
            return cropId;
        }
    }
    return '';
}

function offlineCropClarification(reason) {
    var messages = {
        ambiguous: "Mode hors ligne : vous avez indiqué plusieurs cultures. Nommez une seule culture dans votre question : mil, sorgho, maïs, niébé ou arachide.",
        unsupported: "Mode hors ligne : le conseil engrais pour cette culture n'est pas disponible. Choisissez parmi : mil, sorgho, maïs, niébé ou arachide.",
        missing: "Mode hors ligne : précisez la culture dans votre question : mil, sorgho, maïs, niébé ou arachide."
    };
    return offlineJson({
        answer: messages[reason] || messages.missing,
        confidence: 'Faible',
        sources: [],
        offline: true,
        clarification_required: true
    });
}

function offlineFertilizer(formData) {
    return caches.match('/static/data/fertilizer.json').then(function(response) {
        return response ? response.json() : null;
    }).then(function(table) {
        if (!table || !table.crops) {
            return null;
        }
        var question = String(formData.get('messageText') || '');
        var isFertilizer = (table.keywords || []).some(function(keyword) {
            return normalizeText(question).indexOf(normalizeText(keyword)) !== -1;
        });
        if (!isFertilizer) {
            return null;
        }
        var detected = (table.registry || []).filter(function(item) {
            return [item.id].concat(item.aliases).some(function(alias) { return containsTerm(question, alias); });
        });
        // Multiple or unsupported explicit crops must not inherit a stale selection.
        if (detected.length > 1) { return offlineCropClarification('ambiguous'); }
        if (detected.length === 1 && !table.crops[detected[0].id]) {
            return offlineCropClarification('unsupported');
        }
        var crop = detected.length ? detected[0].id : normalizeCrop(question, table);
        if (!crop && formData.get('prior_question')) { return offlineCropClarification('missing'); }
        crop = crop || normalizeCrop(formData.get('crop'), table);
        if (table.review_expires_at && Date.parse(table.review_expires_at) <= Date.now()) { return null; }
        if (!crop) {
            return offlineCropClarification('missing');
        }
        var item = table.crops[crop];
        if (!item) {
            return offlineCropClarification('unsupported');
        }
        if (item.available === false) {
            return offlineJson({
                answer: 'Mode hors ligne : pour ' + item.label + ', ' + item.lines.join(' '),
                sources: [],
                confidence: 'Faible',
                audio_url: '',
                offline: true,
                saved_at: table.updated_at,
                answer_kind: 'refusal'
            });
        }
        var answer = '🌱 Fumure recommandée pour ' + item.label + ' au Burkina Faso :\n' +
            item.lines.map(function(line) { return '• ' + line; }).join('\n') + '\n\n' + table.disclaimer;
        return offlineJson({
            answer: answer,
            sources: item.sources,
            confidence: 'Fort',
            audio_url: '',
            offline: true,
            saved_at: table.updated_at,
            evidence_status: 'Référence précise à confirmer avec un agent agricole.',
            case: {
                case_title: 'Conseil engrais',
                input_type: 'fertilizer',
                crop: item.label.replace(/^(le |la |l')/, ''),
                summary: 'Fumure recommandée pour ' + item.label + ' au Burkina Faso.',
                actions: item.lines,
                do_not: ["N'augmentez pas les doses sans conseil local.", "Évitez l'urée juste avant une forte pluie si possible."],
                disclaimer: table.disclaimer,
                confirmation: 'Confirmez toujours avec votre agent agricole : la bonne dose dépend de votre sol, de la pluie et de vos moyens.',
                risk_level: 'Faible si confirmé localement',
                sources: item.sources
            }
        });
    });
}

function shouldCacheFirst(url) {
    if (EXTERNAL_SHELL.indexOf(url.href) !== -1) {
        return true;
    }
    if (url.origin !== self.location.origin) {
        return false;
    }
    return SHELL.indexOf(url.pathname) !== -1;
}

async function networkFirstAsk(request) {
    var formData = await request.clone().formData();
    var key = new Request(answerKey(formData));
    var cache = await caches.open(ANSWER_CACHE);
    try {
        var response = await fetch(request.clone());
        if (response.ok && response.headers.get('X-DakiKobo-Cacheable') === '1' && response.headers.get('X-DakiKobo-Corpus')) {
            // Await the write so the worker lifetime includes durable persistence.
            try {
                var corpus = response.headers.get('X-DakiKobo-Corpus');
                var marker = await cache.match('/__corpus__');
                if (marker && (await marker.text()) !== corpus) {
                    await caches.delete(ANSWER_CACHE);
                    cache = await caches.open(ANSWER_CACHE);
                }
                await cache.put('/__corpus__', new Response(corpus));
                await cache.put(key, response.clone());
                var keys = await cache.keys();
                while (keys.length > ANSWER_LIMIT + 1) {
                    var oldest = keys.shift();
                    if (new URL(oldest.url).pathname !== '/__corpus__') { await cache.delete(oldest); }
                }
            } catch (_) { /* Storage full/private mode must not discard the online answer. */ }
        }
        return response;
    } catch (_) {
        var cached = await cache.match(key);
        if (cached) {
            var saved = Number(cached.headers.get('X-DakiKobo-Saved-At')) * 1000;
            var age = Date.now() - saved;
            var marker = await cache.match('/__corpus__');
            if (saved && age >= 0 && age < ANSWER_MAX_AGE_MS && marker &&
                (await marker.text()) === cached.headers.get('X-DakiKobo-Corpus')) {
                var payload = await cached.json();
                payload.offline = true;
                payload.saved_at = new Date(saved).toISOString();
                return offlineJson(payload);
            }
        }
        var fallback = await offlineFertilizer(formData);
        return fallback || offlineJson({
            answer: "Mode hors ligne : ce conseil est absent ou trop ancien. Reconnectez-vous pour une réponse sourcée à jour.",
            confidence: 'Faible', sources: [], offline: true
        }, 503);
    }
}

self.addEventListener('message', function(event) {
    if (event.data && event.data.type === 'CLEAR_SAVED_ANSWERS') {
        event.waitUntil(caches.delete(ANSWER_CACHE).then(function() {
            if (event.ports && event.ports[0]) { event.ports[0].postMessage({ ok: true }); }
        }));
    }
});

self.addEventListener('fetch', function(event) {
    var url = new URL(event.request.url);
    if (event.request.method === 'POST' && url.pathname === '/ask') {
        event.respondWith(networkFirstAsk(event.request));
        return;
    }
    if (event.request.method !== 'GET') {
        return;
    }
    if (shouldCacheFirst(url)) {
        event.respondWith(cacheFirst(event.request));
    }
});

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        normalizeCrop: normalizeCrop,
        networkFirstAsk: networkFirstAsk,
        offlineFertilizer: offlineFertilizer,
        shouldCacheFirst: shouldCacheFirst
    };
}
