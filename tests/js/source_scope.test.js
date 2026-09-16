'use strict';

// Focused DOM regressions for the source-card "Portée et limites" line.
// Uses jsdom plus a minimal jQuery-like shim covering exactly the subset of
// the API that render.js exercises, so we can assert on real DOM output.

const assert = require('node:assert/strict');
const test = require('node:test');
const { JSDOM } = require('jsdom');

const renderFactory = require('../../static/js/render.js');

// Minimal chainable jQuery shim backed by real jsdom nodes.
function makeJquery(documentRef) {
    function wrap(node) {
        return {
            0: node,
            node: node,
            append: function(child) {
                var el = child && child.node ? child.node : child;
                node.appendChild(el);
                return this;
            },
            text: function(value) {
                if (value === undefined) {
                    return node.textContent;
                }
                node.textContent = value == null ? '' : String(value);
                return this;
            },
            attr: function(name, value) {
                node.setAttribute(name, value);
                return this;
            },
            scrollTop: function() { return this; }
        };
    }
    var jq = function(selector) {
        if (typeof selector === 'string' && selector.charAt(0) === '<') {
            var holder = documentRef.createElement('div');
            holder.innerHTML = selector.trim();
            return wrap(holder.firstChild);
        }
        var found = documentRef.querySelector(selector);
        return wrap(found || documentRef.createElement('div'));
    };
    return jq;
}

function renderInto(sources) {
    const dom = new JSDOM('<div class="chat-messages"></div>');
    global.document = dom.window.document;
    const $ = makeJquery(dom.window.document);
    const render = renderFactory.create($);
    const bubble = {
        node: dom.window.document.createElement('div'),
        append: function(child) {
            this.node.appendChild(child && child.node ? child.node : child);
            return this;
        }
    };
    render.renderSources(bubble, sources);
    return bubble.node;
}

test('la portée déclarée d\'une source s\'affiche sous « Portée et limites »', function() {
    const bubble = renderInto([
        {
            title: 'MAERAH/OAPH 2026 - orientation Burkina',
            type: 'Document de programme',
            snippet: 'Orientation nationale des cultures pluviales.',
            scope: 'Orientation nationale ; confirmer les doses avec un agent.'
        }
    ]);
    const scope = bubble.querySelector('.source-scope');
    assert.ok(scope, 'la ligne .source-scope doit exister');
    assert.match(scope.textContent, /Portée et limites\s*:/);
    assert.match(scope.textContent, /Orientation nationale ; confirmer les doses avec un agent\./);
});

test('une source sans portée ne rend aucune ligne « Portée et limites »', function() {
    const bubble = renderInto([
        {
            title: 'guide_mil.pdf',
            type: 'Base locale',
            snippet: 'Semez le mil au début de la saison des pluies.'
        }
    ]);
    assert.equal(bubble.querySelector('.source-scope'), null);
    // The rest of the card still renders.
    assert.ok(bubble.querySelector('.source-title'));
});

test('une portée contenant du balisage s\'affiche littéralement sans exécuter de HTML', function() {
    const bubble = renderInto([
        {
            title: 'Source test',
            type: 'Base locale',
            snippet: '',
            scope: '<img src=x onerror=alert(1)> <script>alert(2)</script>'
        }
    ]);
    const scope = bubble.querySelector('.source-scope');
    assert.ok(scope);
    // The markup is present as visible text, never as live nodes.
    assert.match(scope.textContent, /<img src=x onerror=alert\(1\)>/);
    assert.equal(bubble.querySelector('img'), null);
    assert.equal(bubble.querySelector('script'), null);
});
