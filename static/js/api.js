(function(root) {
    'use strict';

    function signalOfflineFallback(response) {
        if (response.headers && response.headers.get('X-DakiKobo-Offline') === '1' && root.dispatchEvent) {
            root.dispatchEvent(new CustomEvent('dakikobo:offline-fallback'));
        }
    }

    function fetchJson(url, options) {
        return fetch(url, options).then(function(response) {
            signalOfflineFallback(response);
            return response.json().catch(function() {
                return { error: 'Réponse du serveur illisible.' };
            }).then(function(payload) {
                if (!response.ok) {
                    var error = new Error(payload.error || payload.answer || 'Service indisponible.');
                    error.payload = payload;
                    throw error;
                }
                if (payload.offline && payload.saved_at) {
                    var label = 'Conseil enregistré le ' + new Date(payload.saved_at).toLocaleDateString('fr-FR') + ' — vérifiez les conditions actuelles.';
                    payload.answer = label + '\n\n' + (payload.answer || '');
                    if (payload.case) { payload.case.summary = label + ' ' + (payload.case.summary || ''); }
                }
                return payload;
            });
        });
    }

    function formBody(values) {
        var data = new FormData();
        Object.keys(values || {}).forEach(function(key) {
            data.append(key, values[key] == null ? '' : values[key]);
        });
        return data;
    }

    function sendMessage(values) {
        return fetchJson('/ask', { method: 'POST', body: formBody(values) });
    }

    function uploadImageForScreening(file, crop, growthStage, location, simpleFrench, question) {
        var data = formBody({
            crop: crop || '',
            growth_stage: growthStage || '',
            location: location || '',
            simple_french: simpleFrench ? '1' : '0',
            question: question || 'Photo maladie'
        });
        return prepareImage(file).then(function(image) {
            data.append('image', image);
            return fetchJson('/screen', { method: 'POST', body: data });
        });
    }

    function loadWeatherContext(locationId) {
        return fetchJson('/weather?location=' + encodeURIComponent(locationId));
    }

    function loadSoilContext(locationId, cropId) {
        return fetchJson('/soil?location=' + encodeURIComponent(locationId) + '&crop=' + encodeURIComponent(cropId));
    }

    function loadDemoExample(exampleId) {
        return fetchJson('/examples/' + encodeURIComponent(exampleId));
    }

    function loadRegistry() {
        return fetchJson('/registry');
    }

    function loadCropLabels() {
        return fetchJson('/crop-labels');
    }

    var journalReady;
    function ensureJournal() {
        if (!journalReady) {
            journalReady = fetchJson('/journal/session', { cache: 'no-store' }).catch(function(error) {
                journalReady = null;
                throw error;
            });
        }
        return journalReady;
    }
    function submitFeedback(values) {
        return ensureJournal().then(function() {
            return fetchJson('/feedback', { method: 'POST', body: formBody(values) });
        });
    }
    function loadJournal() {
        return ensureJournal().then(function() { return fetchJson('/journal', { cache: 'no-store' }); });
    }
    function deleteJournal(id) {
        return fetchJson('/journal' + (id ? '/' + id : ''), { method: 'DELETE' });
    }
    function clearDeviceData() {
        Object.keys(root.localStorage).forEach(function(key) {
            if (/^dakikobo/i.test(key)) { root.localStorage.removeItem(key); }
        });
        if (!root.caches) { return Promise.resolve(); }
        return root.caches.keys().then(function(keys) {
            return Promise.all(keys.filter(function(key) { return /^dakikobo-.*-answers$/.test(key); }).map(function(key) { return root.caches.delete(key); }));
        });
    }

    // Offline follow-up outcomes: a farmer who records a result without a signal
    // must not lose it. Text-only outcomes are queued durably in localStorage and
    // replayed on reconnection. Photo outcomes are never queued — an unsent image
    // would be silently dropped — so they fail visibly instead.
    var OUTCOME_QUEUE_KEY = 'dakikobo_outcome_queue_v1';

    function readOutcomeQueue() {
        try {
            var raw = root.localStorage && root.localStorage.getItem(OUTCOME_QUEUE_KEY);
            var parsed = raw ? JSON.parse(raw) : [];
            return Array.isArray(parsed) ? parsed : [];
        } catch (_) {
            return [];
        }
    }

    function writeOutcomeQueue(queue) {
        if (!root.localStorage) { return; }
        if (queue && queue.length) {
            root.localStorage.setItem(OUTCOME_QUEUE_KEY, JSON.stringify(queue));
        } else {
            root.localStorage.removeItem(OUTCOME_QUEUE_KEY);
        }
    }

    function pendingOutcomeCount() {
        return readOutcomeQueue().length;
    }

    function enqueueOutcome(feedbackId, outcome) {
        var queue = readOutcomeQueue().filter(function(item) {
            return item && item.feedback_id !== feedbackId;
        });
        queue.push({ feedback_id: feedbackId, outcome: outcome, queued_at: Date.now() });
        writeOutcomeQueue(queue);
    }

    function postOutcome(feedbackId, outcome, file) {
        var data = formBody({ feedback_id: feedbackId, outcome: outcome });
        if (file) {
            data.append('after_image', file);
        }
        return fetchJson('/feedback/outcome', { method: 'POST', body: data });
    }

    function flushOutcomeQueue() {
        var queue = readOutcomeQueue();
        if (!queue.length) { return Promise.resolve(0); }
        var flushed = 0;
        var remaining = [];
        return queue.reduce(function(chain, item) {
            return chain.then(function() {
                return postOutcome(item.feedback_id, item.outcome).then(function() {
                    flushed += 1;
                }).catch(function() {
                    // Keep unsent items for the next reconnection instead of dropping them.
                    remaining.push(item);
                });
            });
        }, Promise.resolve()).then(function() {
            writeOutcomeQueue(remaining);
            return flushed;
        });
    }

    function submitOutcome(feedbackId, outcome, file) {
        if (file) {
            // Photo outcomes cannot be queued (an unsent image would be lost), so
            // surface the failure instead of pretending it was saved.
            return postOutcome(feedbackId, outcome, file);
        }
        return postOutcome(feedbackId, outcome).catch(function(error) {
            // A server that answered (4xx/5xx via fetchJson) genuinely rejected the
            // outcome — do not queue it for endless retries. Only a transport
            // failure (no response, i.e. no payload) means "offline, try later".
            if (error && error.payload) {
                throw error;
            }
            enqueueOutcome(feedbackId, outcome);
            return { ok: true, queued: true };
        });
    }

    if (root.addEventListener) {
        root.addEventListener('online', function() { flushOutcomeQueue(); });
    }
    function prepareImage(file) {
        if (!root.createImageBitmap || !root.document) { return Promise.resolve(file); }
        return root.createImageBitmap(file).then(function(bitmap) {
            var canvas = root.document.createElement('canvas');
            var scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
            canvas.width = Math.max(1, Math.round(bitmap.width * scale));
            canvas.height = Math.max(1, Math.round(bitmap.height * scale));
            canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
            bitmap.close();
            return new Promise(function(resolve) {
                canvas.toBlob(function(blob) { resolve(blob ? new File([blob], 'feuille.jpg', { type: 'image/jpeg' }) : file); }, 'image/jpeg', 0.85);
            });
        }).catch(function() { return file; });
    }

    var exported = {
        fetchJson: fetchJson,
        loadJournal: loadJournal,
        deleteJournal: deleteJournal,
        clearDeviceData: clearDeviceData,
        flushOutcomeQueue: flushOutcomeQueue,
        pendingOutcomeCount: pendingOutcomeCount,
        prepareImage: prepareImage,
        loadCropLabels: loadCropLabels,
        loadDemoExample: loadDemoExample,
        loadRegistry: loadRegistry,
        loadSoilContext: loadSoilContext,
        loadWeatherContext: loadWeatherContext,
        sendMessage: sendMessage,
        submitFeedback: submitFeedback,
        submitOutcome: submitOutcome,
        uploadImageForScreening: uploadImageForScreening
    };
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = exported;
    } else {
        root.DakiKoboApi = exported;
    }
}(typeof window !== 'undefined' ? window : globalThis));
