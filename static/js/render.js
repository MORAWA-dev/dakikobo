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
            $afterBlock.append($('<label class="followup-after-label"></label>').text('Photo après, facultative : enregistrée avec ce conseil pendant 90 jours. Évitez visages et informations personnelles.'));
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
                    $prompt.find('.followup-error').remove();
                    $prompt.append($('<p class="followup-error" role="status"></p>').text('Suivi non enregistré. Vérifiez la connexion ou essayez une autre photo.'));
                });
            });
            bubble.append($prompt);
            scrollChat();
        }

        function renderFeedback(bubble, question, answer, journal) {
            var retentionDays = Number(document.documentElement.dataset.journalRetentionDays || 90);
            var $fb = $('<div class="feedback"></div>');
            var $up = $('<button type="button" class="fb-btn" data-rating="up" aria-label="Réponse utile">👍</button>');
            var $down = $('<button type="button" class="fb-btn" data-rating="down" aria-label="Réponse pas utile">👎</button>');
            $fb.append($('<p></p>').text('Facultatif : enregistrer ce conseil dans mon journal privé pendant ' + retentionDays + ' jours (question et réponse). Accessible sur ce navigateur ; supprimable à tout moment.'));
            var $consent = $('<input type="checkbox">');
            $fb.append($('<label></label>').append($consent).append(document.createTextNode(' Je souhaite enregistrer ce conseil.')));
            var $research = $('<input type="checkbox">');
            $fb.append($('<label></label>').append($research).append(document.createTextNode(' Facultatif : autoriser son utilisation pour améliorer les conseils.')));
            $fb.append($('<p></p>').text('Ce conseil vous semble-t-il utile ?'));
            $fb.append($up).append($down);
            var requestId = root.crypto && root.crypto.randomUUID ? root.crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2);
            var $status = $('<p role="status"></p>');
            $fb.append($status);
            $fb.on('click', '.fb-btn', function() {
                var rating = $(this).data('rating');
                $fb.find('.fb-btn').prop('disabled', true);
                var feedbackData = {
                    rating: rating,
                    consent: $consent.is(':checked') ? '1' : '0',
                    research_consent: $consent.is(':checked') && $research.is(':checked') ? '1' : '0',
                    request_id: requestId,
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
                        $status.text('Conseil enregistré. Retrouvez-le dans « Mes conseils » pour noter le résultat plus tard.');
                    } else {
                        $status.text('Merci. Votre avis a été pris en compte sans enregistrer la question ni la réponse.');
                    }
                }).catch(function() {
                    $fb.find('.fb-btn').prop('disabled', false);
                    $status.text('Enregistrement impossible. Reconnectez-vous et réessayez ; votre conseil reste affiché.');
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
            element.text(message == null ? '' : String(message));
            if (onComplete) { onComplete(); }
        }

        return {
            cleanDisplayText: cleanDisplayText,
            escapeHtml: escapeHtml,
            renderFeedback: renderFeedback,
            renderFollowupPrompt: renderFollowupPrompt,
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
