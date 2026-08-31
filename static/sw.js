'use strict';

var VERSION = 'dakikobo-phase5-v1';
var SHELL_CACHE = VERSION + '-shell';
var ANSWER_CACHE = VERSION + '-answers';
var SHELL = [
    '/',
    '/registry',
    '/crop-labels',
    '/static/manifest.webmanifest',
    '/static/css/style.css',
    '/static/js/render.js',
    '/static/js/api.js',
    '/static/js/index.js',
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

self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(SHELL_CACHE)
            .then(function(cache) {
                return cache.addAll(SHELL).then(function() {
                    return fetch('https://code.jquery.com/jquery-3.6.0.min.js', { mode: 'no-cors' })
                        .then(function(response) { return cache.put('https://code.jquery.com/jquery-3.6.0.min.js', response); })
                        .catch(function() { return Promise.resolve(); });
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

function normalizeCrop(text) {
    var value = String(text || '').toLowerCase();
    if (/\bma[iï]s\b/.test(value)) { return 'mais'; }
    if (/\bni[eé]b[eé]\b/.test(value)) { return 'niebe'; }
    if (/\bsorgho\b/.test(value)) { return 'sorgho'; }
    if (/\bmil\b/.test(value)) { return 'mil'; }
    if (/\barachide\b/.test(value)) { return 'arachide'; }
    return '';
}

function offlineFertilizer(formData) {
    var question = String(formData.get('messageText') || '');
    var crop = normalizeCrop(formData.get('crop')) || normalizeCrop(question);
    var isFertilizer = /engrais|fumure|fertilis|npk|ur[ée]e?|micro-?dose/i.test(question);
    if (!crop || !isFertilizer) {
        return Promise.resolve(null);
    }
    return caches.match('/static/data/fertilizer.json').then(function(response) {
        return response ? response.json() : null;
    }).then(function(table) {
        var item = table && table.crops && table.crops[crop];
        if (!item) {
            return null;
        }
        var answer = '🌱 Fumure recommandée pour ' + item.label + ' au Burkina Faso :\n' +
            item.lines.map(function(line) { return '• ' + line; }).join('\n') + '\n\n' + table.disclaimer;
        return offlineJson({
            answer: answer,
            sources: item.sources,
            confidence: 'Fort',
            audio_url: '',
            offline: true,
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

function networkFirstAsk(request) {
    return request.clone().formData().then(function(formData) {
        var key = new Request(answerKey(formData));
        return fetch(request.clone()).then(function(response) {
            if (response.ok) {
                caches.open(ANSWER_CACHE).then(function(cache) { cache.put(key, response.clone()); });
            }
            return response;
        }).catch(function() {
            return caches.open(ANSWER_CACHE).then(function(cache) { return cache.match(key); })
                .then(function(cached) {
                    if (cached) {
                        return cached.json().then(function(payload) { return offlineJson(payload); });
                    }
                    return offlineFertilizer(formData);
                })
                .then(function(fallback) {
                    return fallback || offlineJson({
                        answer: "Mode hors ligne : cette question n'est pas encore enregistrée. Reconnectez-vous pour obtenir une réponse sourcée.",
                        confidence: 'Faible',
                        sources: [],
                        offline: true
                    }, 503);
                });
        });
    });
}

self.addEventListener('fetch', function(event) {
    var url = new URL(event.request.url);
    if (event.request.method === 'POST' && url.pathname === '/ask') {
        event.respondWith(networkFirstAsk(event.request));
        return;
    }
    if (event.request.method !== 'GET') {
        return;
    }
    if (url.origin === self.location.origin || url.hostname === 'code.jquery.com') {
        event.respondWith(cacheFirst(event.request));
    }
});
