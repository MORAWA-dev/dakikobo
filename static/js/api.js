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

    function submitOutcome(feedbackId, outcome, file) {
        var data = formBody({ feedback_id: feedbackId, outcome: outcome });
        if (file) {
            data.append('after_image', file);
        }
        return fetchJson('/feedback/outcome', { method: 'POST', body: data });
    }

    var exported = {
        fetchJson: fetchJson,
        loadJournal: loadJournal,
        deleteJournal: deleteJournal,
        clearDeviceData: clearDeviceData,
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
