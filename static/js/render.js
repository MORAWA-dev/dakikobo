(function(root) {
    'use strict';

    function create($, apiClient) {
        var api = apiClient || root.DakiKoboApi;
        function scrollChat() {
            var chat = $('.chat-messages')[0];
            if (chat) {
                $('.chat-messages').scrollTop(chat.scrollHeight);
            }
        }

        function cleanDisplayText(text) {
            if (!text || typeof text !== 'string') {
                return '';
            }
            var value = text.replace(/\s+/g, ' ').trim();
            if (/route commerciale|march[eé]s villageois|vente de bois|→/i.test(value) && value.length > 40) {
                return '';
            }
            if ((value.match(/,/g) || []).length >= 5) {
                return '';
            }
            return value;
        }

        function escapeHtml(text) {
            var node = document.createElement('div');
            node.textContent = text == null ? '' : String(text);
            return node.innerHTML;
        }

        function safeSourceUrl(url) {
            if (!url || typeof url !== 'string') {
                return '';
            }
            return /^https?:\/\//i.test(url) ? url : '';
        }

        function sourceMetaItems(src) {
            var items = [];
            [
                ['Éditeur', src.publisher],
                ['Année', src.year],
                ['Pays', src.country],
                ['Revue', src.review_status]
            ].forEach(function(item) {
                if (item[1]) {
                    items.push({ label: item[0], value: item[1] });
                }
            });
            return items;
        }

        function renderFollowupPrompt(bubble, feedbackId) {
            var $prompt = $('<div class="followup-prompt"></div>');
            $prompt.append($('<div class="followup-label"></div>').text('Avez-vous appliqué ce conseil ?'));
            var $options = $('<div class="followup-options"></div>');
            [
                { value: 'applied_improved', label: '✅ Oui, amélioré' },
                { value: 'applied_unchanged', label: '➡️ Pas de changement' },
                { value: 'applied_worse', label: '⚠️ Résultat pire' },
                { value: 'not_applied', label: '❌ Non appliqué' },
                { value: 'not_sure', label: '🤷 Pas sûr' }
            ].forEach(function(item) {
                $options.append(
                    $('<button type="button" class="followup-btn"></button>')
                        .attr('data-outcome', item.value)
                        .text(item.label)
                );
            });
            $prompt.append($options);
            var $afterBlock = $('<div class="followup-after-photo"></div>');
            $afterBlock.append($('<label class="followup-after-label"></label>').text('Photo après (optionnel, pour le suivi de parcelle)'));
            var $afterInput = $('<input type="file" accept="image/*" capture="environment" class="followup-after-input">');
            $afterBlock.append($afterInput);
            $prompt.append($afterBlock);

            $options.on('click', '.followup-btn', function() {
                var outcome = $(this).data('outcome');
                $options.find('.followup-btn').prop('disabled', true);
                $afterInput.prop('disabled', true);
                var file = $afterInput[0] && $afterInput[0].files && $afterInput[0].files[0];
                api.submitOutcome(feedbackId, outcome, file).then(function() {
                    var thanks = 'Merci pour le suivi !';
                    if (file) {
                        thanks += ' Photo après enregistrée pour évaluation (privée).';
                    }
                    $options.after($('<span class="followup-thanks"></span>').text(thanks));
                }).catch(function() {
                    $options.find('.followup-btn').prop('disabled', false);
                    $afterInput.prop('disabled', false);
                });
            });
            bubble.append($prompt);
            scrollChat();
        }

        function renderFeedback(bubble, question, answer, journal) {
            var $fb = $('<div class="feedback"></div>');
            var $up = $('<button type="button" class="fb-btn" data-rating="up" aria-label="Réponse utile">👍</button>');
            var $down = $('<button type="button" class="fb-btn" data-rating="down" aria-label="Réponse pas utile">👎</button>');
            $fb.append($up).append($down);
            $fb.on('click', '.fb-btn', function() {
                var rating = $(this).data('rating');
                $fb.find('.fb-btn').prop('disabled', true);
                var feedbackData = {
                    rating: rating,
                    question: question,
                    answer: answer,
                    crop_id: journal && journal.crop_id ? journal.crop_id : '',
                    place_id: journal && journal.place_id ? journal.place_id : '',
                    answer_path: journal && journal.answer_path ? journal.answer_path : ''
                };
                if (journal && journal.ledger_created_at !== null && journal.ledger_created_at !== undefined) {
                    feedbackData.ledger_created_at = journal.ledger_created_at;
                }
                api.submitFeedback(feedbackData).then(function(response) {
                    $fb.append($('<span class="fb-thanks"></span>').text('Merci !'));
                    if (response && response.feedback_id) {
                        renderFollowupPrompt(bubble, response.feedback_id);
                    }
                }).catch(function() {
                    $fb.find('.fb-btn').prop('disabled', false);
                });
            });
            bubble.append($fb);
            scrollChat();
        }

        function renderSources(bubble, sources) {
            if (!sources || sources.length === 0) {
                return;
            }
            var $box = $('<div class="sources"></div>');
            $box.append($('<span class="sources-label"></span>').text('Sources :'));
            sources.forEach(function(src) {
                if (typeof src === 'string') {
                    $box.append($('<span class="source-chip"></span>').text(src));
                    return;
                }
                var title = src.title || 'Source';
                var url = safeSourceUrl(src.url);
                var $card = $('<div class="source-card"></div>');
                var $top = $('<div class="source-card-top"></div>');
                $top.append($('<span class="source-type"></span>').text(src.type || 'Source'));
                $top.append(url
                    ? $('<a class="source-title source-title-link" target="_blank" rel="noopener noreferrer"></a>').attr('href', url).text(title)
                    : $('<span class="source-title"></span>').text(title));
                $card.append($top);
                var metaItems = sourceMetaItems(src);
                if (metaItems.length) {
                    var $meta = $('<div class="source-meta"></div>');
                    metaItems.forEach(function(item) {
                        var $item = $('<span class="source-meta-item"></span>');
                        $item.append($('<strong></strong>').text(item.label + ' : '));
                        $item.append($('<span></span>').text(item.value));
                        $meta.append($item);
                    });
                    $card.append($meta);
                }
                var snippet = cleanDisplayText(src.snippet || '');
                if (snippet && snippet.length <= 160) {
                    $card.append($('<p class="source-snippet"></p>').text(snippet));
                }
                $box.append($card);
            });
            bubble.append($box);
            scrollChat();
        }

        function typeMessage(message, element, speed, onComplete) {
            var i = 0;
            var rendered = '';
            var safeMessage = message == null ? '' : String(message);
            var interval = speed === undefined ? 15 : speed;
            element.text('');
            var typingInterval = setInterval(function() {
                if (i < safeMessage.length) {
                    rendered += safeMessage.charAt(i);
                    element.text(rendered);
                    i += 1;
                } else {
                    clearInterval(typingInterval);
                    if (typeof onComplete === 'function') {
                        onComplete();
                    }
                }
                scrollChat();
            }, interval);
        }

        return {
            cleanDisplayText: cleanDisplayText,
            escapeHtml: escapeHtml,
            renderFeedback: renderFeedback,
            renderSources: renderSources,
            safeSourceUrl: safeSourceUrl,
            sourceMetaItems: sourceMetaItems,
            typeMessage: typeMessage
        };
    }

    var exported = { create: create };
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = exported;
    } else {
        root.DakiKoboRender = exported;
    }
}(typeof window !== 'undefined' ? window : globalThis));
