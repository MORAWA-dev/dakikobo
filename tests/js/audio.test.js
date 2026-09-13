'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { JSDOM } = require('jsdom');
const read = name => fs.readFileSync(path.join(__dirname, '../../static/', name), 'utf8');

async function until(predicate) {
    for (let n = 0; n < 100; n++) {
        if (predicate()) { return; }
        await new Promise(resolve => setTimeout(resolve, 10));
    }
    assert.fail('UI did not reach the expected state');
}

for (const failureMode of ['rejection', 'media-error']) {
test(`un audio indisponible (${failureMode}) permet de réessayer sans perdre le conseil`, async () => {
    const dom = new JSDOM('<div class="chat-messages"></div><textarea id="messageText"></textarea><button id="chatbot-form-btn"></button>',
        { url: 'https://dakikobo.test', runScripts: 'outside-only' });
    const w = dom.window;
    w.speechSynthesis = { getVoices: () => [], speaking: false, cancel() {}, speak() {} };
    w.SpeechSynthesisUtterance = function(text) { this.text = text; };
    let available = false;
    let playCount = 0;
    w.Audio = class {
        constructor() { this.paused = true; this.handlers = {}; }
        addEventListener(name, handler) { this.handlers[name] = handler; }
        pause() {}
        play() {
            playCount++;
            if (available) { return Promise.resolve(); }
            if (failureMode === 'rejection') { return Promise.reject(new Error('audio 404')); }
            w.setTimeout(() => this.handlers.error(), 0);
            return Promise.resolve();
        }
    };
    w.DakiKoboApi = {
        loadRegistry: async () => ({}), loadCropLabels: async () => ({}),
        sendMessage: async () => ({ answer: 'Conseil conservé.', sources: [], audio_url: '/static/audio/expired.mp3' })
    };
    try {
        w.eval(read('vendor/jquery-3.6.0.min.js'));
        w.eval(read('js/render.js'));
        w.eval(read('js/index.js'));
        await new Promise(resolve => w.$(resolve));
        w.$('#messageText').val('Mon mil');
        w.$('#chatbot-form-btn').trigger('click');
        await until(() => w.document.querySelector('.audio-replay'));
        w.document.querySelector('.audio-replay').click();
        await until(() => w.document.querySelector('.audio-status')?.textContent);
        const status = w.document.querySelector('.audio-status');
        assert.equal(status.getAttribute('role'), 'status');
        assert.match(status.textContent, /audio.*indisponible/i);
        assert.match(status.textContent, /texte/i);
        assert.match(w.document.querySelector('.chat-messages').textContent, /Conseil conservé\./);
        available = true;
        w.document.querySelector('.audio-replay').click();
        assert.equal(playCount, 2);
        assert.equal(status.textContent, '');
    } finally { dom.window.close(); }
});

}
