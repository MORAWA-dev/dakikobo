'use strict';

var VERSION = 'dakikobo-phase5-v2';
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
var EXTERNAL_SHELL = [
    'https://code.jquery.com/jquery-3.6.0.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/webfonts/fa-solid-900.woff2'
];

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

function offlineFertilizer(formData) {
    return caches.match('/static/data/fertilizer.json').then(function(response) {
        return response ? response.json() : null;
    }).then(function(table) {
        var question = String(formData.get('messageText') || '');
        var crop = normalizeCrop(formData.get('crop'), table) || normalizeCrop(question, table);
        var isFertilizer = table && (table.keywords || []).some(function(keyword) {
            return normalizeText(question).indexOf(normalizeText(keyword)) !== -1;
        });
        if (!crop || !isFertilizer) {
            return null;
        }
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

function shouldCacheFirst(url) {
    if (EXTERNAL_SHELL.indexOf(url.href) !== -1) {
        return true;
    }
    if (url.origin !== self.location.origin) {
        return false;
    }
    return SHELL.indexOf(url.pathname) !== -1;
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
    if (shouldCacheFirst(url)) {
        event.respondWith(cacheFirst(event.request));
    }
});

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        normalizeCrop: normalizeCrop,
        offlineFertilizer: offlineFertilizer,
        shouldCacheFirst: shouldCacheFirst
    };
}
