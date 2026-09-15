'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { JSDOM } = require('jsdom');

const read = name => fs.readFileSync(path.join(__dirname, '../../static/', name), 'utf8');

async function until(predicate) {
    for (let attempt = 0; attempt < 100; attempt++) {
        if (predicate()) { return; }
        await new Promise(resolve => setTimeout(resolve, 10));
    }
    assert.fail('Voice UI did not reach the expected state');
}

test('un refus de permission micro conserve la question et propose la saisie', async () => {
    const dom = new JSDOM(
        '<div class="chat-messages"></div>' +
        '<input id="messageText"><p id="inputHint"></p>' +
        '<button id="chatbot-form-btn"></button>' +
        '<button id="chatbot-form-btn-voice" aria-label="Dicter une question"></button>' +
        '<button id="chatbot-form-btn-image"></button><button id="toolsToggle"></button>',
        { url: 'https://dakikobo.test', runScripts: 'outside-only' }
    );
    const w = dom.window;
    Object.defineProperty(w, 'isSecureContext', { configurable: true, value: true });
    w.console.error = function() {};
    w.speechSynthesis = { getVoices: () => [], speaking: false, cancel() {}, speak() {} };
    w.SpeechSynthesisUtterance = function() {};
    w.MediaRecorder = function() {};
    const denied = new Error('permission denied');
    denied.name = 'NotAllowedError';
    Object.defineProperty(w.navigator, 'mediaDevices', {
        configurable: true,
        value: { getUserMedia: async () => { throw denied; } }
    });
    w.DakiKoboApi = {
        loadRegistry: async () => ({}),
        loadCropLabels: async () => ({})
    };
    try {
        w.eval(read('vendor/jquery-3.6.0.min.js'));
        w.eval(read('js/render.js'));
        w.eval(read('js/index.js'));
        await new Promise(resolve => w.$(resolve));
        w.$('#messageText').val('Mon mil jaunit');
        w.$('#chatbot-form-btn-voice').trigger('click');
        await until(() => /micro est bloqué/i.test(w.document.querySelector('.chat-messages').textContent));
        assert.equal(w.$('#messageText').val(), 'Mon mil jaunit');
        assert.equal(w.$('#messageText').prop('disabled'), false);
        assert.match(w.document.querySelector('.chat-messages').textContent, /taper votre question/i);
        assert.equal(w.$('#chatbot-form-btn-voice').attr('aria-label'), 'Dicter une question');
    } finally {
        dom.window.close();
    }
});
