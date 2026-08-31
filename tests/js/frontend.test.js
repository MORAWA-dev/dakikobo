'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
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
