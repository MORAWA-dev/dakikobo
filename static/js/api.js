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
        data.append('image', file);
        return fetchJson('/screen', { method: 'POST', body: data });
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

    var exported = {
        fetchJson: fetchJson,
        loadCropLabels: loadCropLabels,
        loadDemoExample: loadDemoExample,
        loadRegistry: loadRegistry,
        loadSoilContext: loadSoilContext,
        loadWeatherContext: loadWeatherContext,
        sendMessage: sendMessage,
        uploadImageForScreening: uploadImageForScreening
    };
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = exported;
    } else {
        root.DakiKoboApi = exported;
    }
}(typeof window !== 'undefined' ? window : globalThis));
