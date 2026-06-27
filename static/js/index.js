$(function() {
    var BOT_AVATAR = '/static/images/logo.png';
    var BOT_AVATAR_ALT = 'Logo DakiKobo';

    // Note: We keep the synth/msg variables, but primarily use the <audio> element due to cross-browser issues with SpeechSynthesis.
    var synth = window.speechSynthesis;
    var msg = new SpeechSynthesisUtterance();
    var voices = synth.getVoices();
    if (voices.length > 0) {
        // Try to select a French voice if available, though gTTS is providing the audio file.
        msg.voice = voices.find(v => v.lang.startsWith('fr')) || voices[0]; 
    }
    msg.rate = 1;
    msg.pitch = 1;
    var currentAudio = null;
    var credibilityLastFocus = null;

    function setCredibilityOpen(open) {
        var $modal = $('#credibilityModal');
        var $toggle = $('#credibilityToggle');
        $modal.prop('hidden', !open);
        $toggle
            .attr('aria-expanded', open ? 'true' : 'false')
            .toggleClass('active', open);
        if (open) {
            credibilityLastFocus = document.activeElement;
            $('#credibilityClose').trigger('focus');
        } else if (credibilityLastFocus && document.contains(credibilityLastFocus)) {
            credibilityLastFocus.focus();
            credibilityLastFocus = null;
        }
    }

    $('#credibilityToggle').on('click', function() {
        setCredibilityOpen($('#credibilityModal').prop('hidden'));
    });

    $('#credibilityClose').on('click', function() {
        setCredibilityOpen(false);
    });

    $('#credibilityModal').on('click', function(e) {
        if (e.target === this) {
            setCredibilityOpen(false);
        }
    });

    $(document).on('keydown', function(e) {
        if (e.key === 'Escape' && !$('#credibilityModal').prop('hidden')) {
            setCredibilityOpen(false);
        }
    });

    function stopCurrentAudio() {
        if (currentAudio) {
            currentAudio.pause();
            currentAudio.currentTime = 0;
            currentAudio = null;
        }
        if (synth.speaking) {
            synth.cancel();
        }
    }

    function playAudio(audioUrl) {
        if (!audioUrl) {
            return;
        }
        stopCurrentAudio();
        currentAudio = new Audio(audioUrl);
        currentAudio.addEventListener('ended', function() {
            currentAudio = null;
        });
        currentAudio.play().catch(function(err) {
            console.error("Erreur de lecture audio :", err);
        });
    }

    function renderAudioReplay(bubble, audioUrl) {
        if (!audioUrl) {
            return;
        }
        var $actions = $('<div class="audio-actions"></div>');
        var $button = $('<button type="button" class="audio-replay" aria-label="Réécouter la réponse" title="Réécouter la réponse"></button>');
        $button.append($('<i class="fas fa-volume-up" aria-hidden="true"></i>'));
        $button.append($('<span></span>').text('Réécouter'));
        $button.on('click', function() {
            playAudio(audioUrl);
        });
        $actions.append($button);
        bubble.append($actions);
        $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
    }

    function appendMessage(message, isUser, sources, question, confidence, audioUrl) {
        var messageClass = isUser ? 'user-message' : 'bot-message';
        // Updated logo reference to DakiKobo
        var logoHTML = isUser ? '' : '<div class="bot-logo"><img src="' + BOT_AVATAR + '" alt="' + BOT_AVATAR_ALT + '"></div>';
        var userImageHTML = isUser ? '<div class="user-image"><img src="/static/images/user_avatar.png" alt="User"></div>' : '';
        var messageElement = $('<div class="message-container ' + (isUser ? 'user-container' : 'bot-container') + '">' + 
                            logoHTML + 
                            '<div class="message ' + messageClass + '"></div>' +
                            userImageHTML +
                           '</div>');
        $('.chat-messages').append(messageElement);

        if (isUser) {
            messageElement.find('.message').text(message);
        } else {
            // Render source chips + feedback only once the answer has finished typing.
            var bubble = messageElement.find('.message');
            typeMessage(message, bubble, 15, function() {
                renderConfidence(bubble, confidence);
                renderSources(bubble, sources);
                renderAudioReplay(bubble, audioUrl);
                if (question) {
                    renderFeedback(bubble, question, message);
                }
            });
        }

        $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
        return messageElement;
    }

    function renderFeedback(bubble, question, answer) {
        var $fb = $('<div class="feedback"></div>');
        var $up = $('<button type="button" class="fb-btn" data-rating="up" aria-label="Réponse utile">👍</button>');
        var $down = $('<button type="button" class="fb-btn" data-rating="down" aria-label="Réponse pas utile">👎</button>');
        $fb.append($up).append($down);

        $fb.on('click', '.fb-btn', function() {
            var rating = $(this).data('rating');
            $fb.find('.fb-btn').prop('disabled', true);
            $.post('/feedback', { rating: rating, question: question, answer: answer })
                .done(function() {
                    $fb.append($('<span class="fb-thanks"></span>').text('Merci !'));
                })
                .fail(function() {
                    $fb.find('.fb-btn').prop('disabled', false);
                });
        });

        bubble.append($fb);
        $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
    }

    function confidenceClass(confidence) {
        var value = (confidence || '').toString().toLowerCase();
        if (value === 'fort') {
            return 'confidence-fort';
        }
        if (value === 'faible') {
            return 'confidence-faible';
        }
        return 'confidence-moyen';
    }

    function renderConfidence(bubble, confidence) {
        if (!confidence) {
            return;
        }
        var $line = $('<div class="confidence-line"></div>');
        $line.append(
            $('<span class="confidence-pill"></span>')
                .addClass(confidenceClass(confidence))
                .text('Confiance : ' + confidence)
        );
        bubble.append($line);
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
            var type = src.type || 'Source';
            var snippet = src.snippet || '';
            var $card = $('<div class="source-card"></div>');
            var $top = $('<div class="source-card-top"></div>');
            $top.append($('<span class="source-type"></span>').text(type));
            $top.append($('<span class="source-title"></span>').text(title));
            $card.append($top);
            if (snippet) {
                $card.append($('<p class="source-snippet"></p>').text(snippet));
            }
            $box.append($card);
        });
        bubble.append($box);
        $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
    }

    function asList(value) {
        if (!value) {
            return [];
        }
        if (Array.isArray(value)) {
            return value.filter(Boolean);
        }
        return [value];
    }

    function renderCaseSection($case, title, values) {
        var items = asList(values);
        if (items.length === 0) {
            return;
        }
        var $section = $('<div class="case-section"></div>');
        $section.append($('<div class="case-section-title"></div>').text(title));
        var $list = $('<ul></ul>');
        items.forEach(function(item) {
            $list.append($('<li></li>').text(item));
        });
        $section.append($list);
        $case.append($section);
    }

    function appendCaseMessage(caseData, fallbackAnswer, sources, confidenceOverride, audioUrl) {
        var logoHTML = '<div class="bot-logo"><img src="' + BOT_AVATAR + '" alt="' + BOT_AVATAR_ALT + '"></div>';
        var messageElement = $('<div class="message-container bot-container">' +
                            logoHTML +
                            '<div class="message bot-message case-message"></div>' +
                           '</div>');
        var bubble = messageElement.find('.message');
        var $case = $('<div class="diagnostic-case"></div>');
        var confidence = confidenceOverride || (caseData && caseData.confidence ? caseData.confidence : 'Moyen');
        var risk = caseData && caseData.risk_level ? caseData.risk_level : 'À vérifier';

        var $head = $('<div class="case-head"></div>');
        $head.append($('<div class="case-title"></div>').text('Cas de terrain - feuille'));
        var $badges = $('<div class="case-badges"></div>');
        $badges.append(
            $('<span class="case-badge confidence"></span>')
                .addClass(confidenceClass(confidence))
                .text('Confiance : ' + confidence)
        );
        $badges.append($('<span class="case-badge risk"></span>').text(risk));
        $head.append($badges);
        $case.append($head);

        if (caseData) {
            var meta = [];
            if (caseData.crop) {
                meta.push('Culture : ' + caseData.crop);
            }
            if (caseData.growth_stage) {
                meta.push('Stade : ' + caseData.growth_stage);
            }
            if (caseData.location) {
                meta.push('Lieu : ' + caseData.location);
            }
            if (meta.length) {
                var $meta = $('<div class="case-meta"></div>');
                meta.forEach(function(item) {
                    $meta.append($('<span></span>').text(item));
                });
                $case.append($meta);
            }
            renderCaseSection($case, 'Observations', caseData.observations);
            renderCaseSection($case, 'Problèmes possibles', caseData.possible_causes);
            renderCaseSection($case, 'Actions immédiates', caseData.actions);
            if (caseData.confirmation) {
                renderCaseSection($case, 'À confirmer', [caseData.confirmation]);
            }
            if (caseData.disclaimer) {
                $case.append($('<p class="case-disclaimer"></p>').text(caseData.disclaimer));
            }
        } else {
            renderCaseSection($case, 'Reponse', [fallbackAnswer]);
        }

        bubble.append($case);
        renderSources(bubble, caseData && caseData.sources ? caseData.sources : sources);
        renderAudioReplay(bubble, audioUrl);
        $('.chat-messages').append(messageElement);
        $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
        return messageElement;
    }

    function weatherStatusClass(status) {
        if (status === 'good') {
            return 'weather-good';
        }
        if (status === 'risk') {
            return 'weather-risk';
        }
        return 'weather-watch';
    }

    function formatWeatherMetric(value, unit) {
        if (value === null || value === undefined || value === '') {
            return 'n.d.';
        }
        return value + unit;
    }

    function appendWeatherMessage(weather) {
        var logoHTML = '<div class="bot-logo"><img src="' + BOT_AVATAR + '" alt="' + BOT_AVATAR_ALT + '"></div>';
        var messageElement = $('<div class="message-container bot-container">' +
                            logoHTML +
                            '<div class="message bot-message weather-message"></div>' +
                           '</div>');
        var bubble = messageElement.find('.message');
        var $card = $('<div class="weather-card"></div>');
        var location = weather.location || {};
        var metrics = weather.metrics || {};

        var $head = $('<div class="weather-head"></div>');
        $head.append($('<div class="weather-title"></div>').text('Météo agricole - ' + (location.name || 'Localité')));
        if (weather.updated_at) {
            $head.append($('<div class="weather-updated"></div>').text('Mise à jour : ' + weather.updated_at));
        }
        $card.append($head);

        var $metrics = $('<div class="weather-metrics"></div>');
        [
            ['Pluie 7 j', formatWeatherMetric(metrics.rain_7d_mm, ' mm')],
            ['Pluie 3 j', formatWeatherMetric(metrics.rain_next_3d_mm, ' mm')],
            ['ET0 7 j', formatWeatherMetric(metrics.et0_7d_mm, ' mm')],
            ['Humidité sol', metrics.soil_moisture_signal || 'n.d.']
        ].forEach(function(item) {
            var $metric = $('<div class="weather-metric"></div>');
            $metric.append($('<span></span>').text(item[0]));
            $metric.append($('<strong></strong>').text(item[1]));
            $metrics.append($metric);
        });
        $card.append($metrics);

        var $insights = $('<div class="weather-insights"></div>');
        (weather.insights || []).forEach(function(insight) {
            var $item = $('<div class="weather-insight"></div>').addClass(weatherStatusClass(insight.status));
            $item.append($('<div class="weather-insight-label"></div>').text(insight.label || 'Signal'));
            $item.append($('<p></p>').text(insight.text || ''));
            $insights.append($item);
        });
        $card.append($insights);

        if (weather.disclaimer) {
            $card.append($('<p class="weather-disclaimer"></p>').text(weather.disclaimer));
        }

        bubble.append($card);
        renderSources(bubble, weather.sources);
        $('.chat-messages').append(messageElement);
        $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
        return messageElement;
    }

    function formatSoilMetric(value, unit) {
        if (value === null || value === undefined || value === '') {
            return 'n.d.';
        }
        return value + unit;
    }

    function appendSoilMessage(soil, fertilizer, confidence) {
        var logoHTML = '<div class="bot-logo"><img src="' + BOT_AVATAR + '" alt="' + BOT_AVATAR_ALT + '"></div>';
        var messageElement = $('<div class="message-container bot-container">' +
                            logoHTML +
                            '<div class="message bot-message soil-message"></div>' +
                           '</div>');
        var bubble = messageElement.find('.message');
        var $card = $('<div class="soil-card"></div>');
        var location = soil.location || {};
        var metrics = soil.metrics || {};

        var $head = $('<div class="soil-head"></div>');
        $head.append($('<div class="soil-title"></div>').text('Sol + engrais - ' + (location.name || 'Localité')));
        $head.append($('<div class="soil-subtitle"></div>').text('Culture : ' + (soil.crop || 'culture') + ' · profondeur ' + (soil.depth || '0-5 cm')));
        $card.append($head);

        var $metrics = $('<div class="soil-metrics"></div>');
        [
            ['Argile', formatSoilMetric(metrics.clay_percent, ' %')],
            ['Sable', formatSoilMetric(metrics.sand_percent, ' %')],
            ['Carbone org.', formatSoilMetric(metrics.soc_percent, ' %')],
            ['pH', formatSoilMetric(metrics.ph_h2o, '')]
        ].forEach(function(item) {
            var $metric = $('<div class="soil-metric"></div>');
            $metric.append($('<span></span>').text(item[0]));
            $metric.append($('<strong></strong>').text(item[1]));
            $metrics.append($metric);
        });
        $card.append($metrics);

        var $indicators = $('<div class="soil-indicators"></div>');
        (soil.indicators || []).forEach(function(indicator) {
            var $item = $('<div class="soil-indicator"></div>').addClass(weatherStatusClass(indicator.status));
            $item.append($('<div class="soil-indicator-label"></div>').text(indicator.label || 'Indicateur'));
            $item.append($('<strong></strong>').text(indicator.value || 'À vérifier'));
            $item.append($('<p></p>').text(indicator.text || ''));
            $indicators.append($item);
        });
        $card.append($indicators);

        if (fertilizer && fertilizer.answer) {
            var $fertilizer = $('<div class="soil-fertilizer"></div>');
            $fertilizer.append($('<div class="soil-section-title"></div>').text('Fumure déterministe'));
            $fertilizer.append($('<p></p>').text(fertilizer.answer));
            $card.append($fertilizer);
        }

        if (soil.disclaimer) {
            $card.append($('<p class="soil-disclaimer"></p>').text(soil.disclaimer));
        }

        bubble.append($card);
        renderConfidence(bubble, confidence);
        renderSources(bubble, (soil.sources || []).concat((fertilizer && fertilizer.sources) || []));
        $('.chat-messages').append(messageElement);
        $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
        return messageElement;
    }

    function typeMessage(message, element, speed = 15, onComplete) {
        let i = 0;
        element.html('');
        const typingInterval = setInterval(() => {
            if (i < message.length) {
                element.html(element.html() + message.charAt(i));
                i++;
            } else {
                clearInterval(typingInterval);
                if (typeof onComplete === 'function') {
                    onComplete();
                }
            }
            $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
        }, speed);
    }

    function showTypingIndicator() {
        var typingIndicator = $('<div class="typing-indicator bot-message"><span></span><span></span><span></span></div>');
        $('.chat-messages').append(typingIndicator);
        $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
    }

    function removeTypingIndicator() {
        $('.typing-indicator').remove();
    }

    $('#chatbot-form-btn').click(function(e) {
        e.preventDefault();
        sendMessage();
    });

    $('.examples-panel').on('click', '.example-card', function(e) {
        e.preventDefault();
        if (isProcessing) {
            return;
        }
        var exampleId = $(this).data('example-id');
        var prompt = $(this).data('prompt') || $(this).find('.example-text').text();
        loadDemoExample(exampleId, prompt);
    });

    $('#messageText').keypress(function(e) {
        if (e.which == 13) {
            e.preventDefault();
            sendMessage();
        }
    });

    var isProcessing = false;

    function setToolsOpen(open) {
        $('#toolsDrawer').prop('hidden', !open);
        $('#toolsToggle')
            .attr('aria-expanded', open ? 'true' : 'false')
            .toggleClass('active', open);
    }

    $('#toolsToggle').click(function(e) {
        e.preventDefault();
        if (isProcessing) {
            return;
        }
        setToolsOpen($('#toolsDrawer').prop('hidden'));
    });

    function disableInput() {
        $('#messageText').prop('disabled', true);
        $('#chatbot-form-btn').prop('disabled', true);
        $('#chatbot-form-btn-voice').prop('disabled', true);
        $('#chatbot-form-btn-image').prop('disabled', true);
        $('#toolsToggle').prop('disabled', true);
        $('.example-card').prop('disabled', true);
        $('#weatherLocation').prop('disabled', true);
        $('#weatherBtn').prop('disabled', true);
        $('#soilCrop').prop('disabled', true);
        $('#soilLocation').prop('disabled', true);
        $('#soilBtn').prop('disabled', true);
    }

    function enableInput() {
        $('#messageText').prop('disabled', false);
        $('#chatbot-form-btn').prop('disabled', false);
        $('#chatbot-form-btn-voice').prop('disabled', false);
        $('#chatbot-form-btn-image').prop('disabled', false);
        $('#toolsToggle').prop('disabled', false);
        $('.example-card').prop('disabled', false);
        $('#weatherLocation').prop('disabled', false);
        $('#weatherBtn').prop('disabled', false);
        $('#soilCrop').prop('disabled', false);
        $('#soilLocation').prop('disabled', false);
        $('#soilBtn').prop('disabled', false);
    }

    function loadDemoExample(exampleId, prompt) {
        if (!exampleId || isProcessing) {
            return;
        }
        isProcessing = true;
        disableInput();
        appendMessage(prompt, true);
        showTypingIndicator();

        $.ajax({
            type: "GET",
            url: "/examples/" + encodeURIComponent(exampleId),
            success: function(response) {
                removeTypingIndicator();
                if (response.error) {
                    appendMessage("Erreur : " + response.error, false, null, null, response.confidence);
                } else if (response.case) {
                    appendCaseMessage(response.case, response.answer, response.sources, response.confidence);
                } else {
                    appendMessage(response.answer, false, response.sources, null, response.confidence);
                }
                isProcessing = false;
                enableInput();
            },
            error: function() {
                removeTypingIndicator();
                appendMessage("Désolé, cet exemple n'est pas disponible pour le moment.", false, null, null, 'Faible');
                isProcessing = false;
                enableInput();
            }
        });
    }

    function loadWeatherContext(locationId, locationName) {
        if (!locationId || isProcessing) {
            return;
        }
        setToolsOpen(false);
        isProcessing = true;
        disableInput();
        appendMessage('Météo agricole - ' + locationName, true);
        showTypingIndicator();

        $.ajax({
            type: "GET",
            url: "/weather",
            data: { location: locationId },
            success: function(response) {
                removeTypingIndicator();
                if (response.error) {
                    appendMessage("Erreur : " + response.error, false, null, null, response.confidence);
                } else {
                    appendWeatherMessage(response.weather);
                }
                isProcessing = false;
                enableInput();
            },
            error: function() {
                removeTypingIndicator();
                appendMessage("Désolé, la météo agricole n'est pas disponible pour le moment.", false, null, null, 'Faible');
                isProcessing = false;
                enableInput();
            }
        });
    }

    function loadSoilContext(locationId, locationName, cropId, cropName) {
        if (!locationId || !cropId || isProcessing) {
            return;
        }
        setToolsOpen(false);
        isProcessing = true;
        disableInput();
        appendMessage('Sol + engrais - ' + cropName + ' / ' + locationName, true);
        showTypingIndicator();

        $.ajax({
            type: "GET",
            url: "/soil",
            data: { location: locationId, crop: cropId },
            success: function(response) {
                removeTypingIndicator();
                if (response.error) {
                    appendMessage("Erreur : " + response.error, false, null, null, response.confidence);
                } else {
                    appendSoilMessage(response.soil, response.fertilizer, response.confidence);
                }
                isProcessing = false;
                enableInput();
            },
            error: function() {
                removeTypingIndicator();
                appendMessage("Désolé, le contexte sol n'est pas disponible pour le moment.", false, null, null, 'Faible');
                isProcessing = false;
                enableInput();
            }
        });
    }

    function sendMessage() {
        var message = $('#messageText').val().trim();
        if (message && !isProcessing) {
            isProcessing = true;
            disableInput();
            
            // Append user message
            appendMessage(message, true); 
            $('#messageText').val('');
            showTypingIndicator();

            $.ajax({
                type: "POST",
                url: "/ask",
                data: { messageText: message },
                success: function(response) {
                    removeTypingIndicator();
                    if (response.error) {
                        appendMessage("Erreur : " + response.error, false, null, null, response.confidence);
                    } else {
                        var answer = response.answer;
                        var audioUrl = response.audio_url; // <-- Retrieve the audio URL from Flask
                        var sources = response.sources;    // <-- Source filenames from RAG

                        // Append bot message (with source chips + feedback)
                        appendMessage(answer, false, sources, message, response.confidence, audioUrl);

                        if ($('#voiceReadingCheckbox').is(':checked') && audioUrl) {
                            playAudio(audioUrl);
                        }
                    }
                    isProcessing = false;
                    enableInput();
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    removeTypingIndicator();
                    console.log(errorThrown);
                    appendMessage("Désolé, une erreur est survenue pendant le traitement. Veuillez réessayer plus tard.", false, null, null, 'Faible');
                    isProcessing = false;
                    enableInput();
                }
            });
        }
    }

    function appendImageMessage(dataUrl) {
        var el = $('<div class="message-container user-container">' +
                   '<div class="message user-message"></div>' +
                   '<div class="user-image"><img src="/static/images/user_avatar.png" alt="User"></div>' +
                   '</div>');
        el.find('.message').append($('<img class="msg-image" alt="photo">').attr('src', dataUrl));
        $('.chat-messages').append(el);
        $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
    }

    function appendImageContextForm(file) {
        var logoHTML = '<div class="bot-logo"><img src="' + BOT_AVATAR + '" alt="' + BOT_AVATAR_ALT + '"></div>';
        var messageElement = $('<div class="message-container bot-container">' +
                            logoHTML +
                            '<div class="message bot-message context-message"></div>' +
                           '</div>');
        var bubble = messageElement.find('.message');
        var $form = $('<form class="image-context-form"></form>');

        $form.append($('<div class="context-title"></div>').text("Avant l'analyse"));

        var $grid = $('<div class="context-grid"></div>');
        var $crop = $('<select name="crop" aria-label="Culture"></select>');
        [
            ['', 'Culture : je ne sais pas'],
            ['maïs', 'Maïs'],
            ['mil', 'Mil'],
            ['sorgho', 'Sorgho'],
            ['niébé', 'Niébé'],
            ['arachide', 'Arachide'],
            ['autre', 'Autre culture']
        ].forEach(function(opt) {
            $crop.append($('<option></option>').val(opt[0]).text(opt[1]));
        });

        var $stage = $('<select name="growth_stage" aria-label="Stade de croissance"></select>');
        [
            ['', 'Stade : je ne sais pas'],
            ['levée / jeune plant', 'Levée / jeune plant'],
            ['croissance végétative', 'Croissance végétative'],
            ['floraison', 'Floraison'],
            ['fructification / épi', 'Fructification / épi'],
            ['maturité', 'Maturité']
        ].forEach(function(opt) {
            $stage.append($('<option></option>').val(opt[0]).text(opt[1]));
        });

        var $location = $('<input type="text" name="location" maxlength="120" autocomplete="off" placeholder="Commune ou village (optionnel)">');
        $grid.append($crop).append($stage).append($location);

        var $actions = $('<div class="context-actions"></div>');
        var $submit = $('<button type="submit" class="context-submit">Analyser</button>');
        var $skip = $('<button type="button" class="context-skip">Je ne sais pas</button>');
        $actions.append($submit).append($skip);

        $form.append($grid).append($actions);
        bubble.append($form);
        $('.chat-messages').append(messageElement);
        $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);

        function submitContext(useUnknown) {
            var context = {
                crop: useUnknown ? '' : $crop.val(),
                growth_stage: useUnknown ? '' : $stage.val(),
                location: useUnknown ? '' : $location.val().trim()
            };
            $form.find('input, select, button').prop('disabled', true);
            $form.addClass('submitted');
            uploadImageForScreening(file, context);
        }

        $form.on('submit', function(e) {
            e.preventDefault();
            submitContext(false);
        });

        $skip.on('click', function() {
            submitContext(true);
        });
    }

    function uploadImageForScreening(file, context) {
        var formData = new FormData();
        formData.append('image', file);
        formData.append('crop', context.crop || '');
        formData.append('growth_stage', context.growth_stage || '');
        formData.append('location', context.location || '');
        showTypingIndicator();

        $.ajax({
            type: "POST",
            url: "/screen",
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                removeTypingIndicator();
                if (response.error) {
                    appendMessage("Erreur : " + response.error, false, null, null, response.confidence);
                } else {
                    if (response.case) {
                        appendCaseMessage(response.case, response.answer, response.sources, response.confidence, response.audio_url);
                    } else {
                        appendMessage(response.answer, false, response.sources, null, response.confidence, response.audio_url);
                    }
                    if ($('#voiceReadingCheckbox').is(':checked') && response.audio_url) {
                        playAudio(response.audio_url);
                    }
                }
                isProcessing = false;
                enableInput();
            },
            error: function() {
                removeTypingIndicator();
                appendMessage("Désolé, l'analyse de l'image a échoué. Veuillez réessayer.", false, null, null, 'Faible');
                isProcessing = false;
                enableInput();
            }
        });
    }

    // Leaf-photo disease screening (Gemini Vision via /screen)
    $('#chatbot-form-btn-image').click(function(e) {
        e.preventDefault();
        if (!isProcessing) {
            $('#imageInput').click();
        }
    });

    $('#imageInput').change(function() {
        var file = this.files[0];
        this.value = '';  // allow re-selecting the same file later
        if (!file || isProcessing) {
            return;
        }
        isProcessing = true;
        disableInput();

        var reader = new FileReader();
        reader.onload = function(ev) {
            appendImageMessage(ev.target.result);
            appendImageContextForm(file);
        };
        reader.readAsDataURL(file);
    });

    $('#weatherBtn').click(function(e) {
        e.preventDefault();
        if (isProcessing) {
            return;
        }
        var $selected = $('#weatherLocation option:selected');
        loadWeatherContext($selected.val(), $selected.text());
    });

    $('#soilBtn').click(function(e) {
        e.preventDefault();
        if (isProcessing) {
            return;
        }
        var $location = $('#soilLocation option:selected');
        var $crop = $('#soilCrop option:selected');
        loadSoilContext($location.val(), $location.text(), $crop.val(), $crop.text());
    });

    // Welcome message (French — primary language for Burkina Faso farmers)
    var welcomeMessage = "🌾 Bienvenue à DakiKobo ! 💡 Je suis DakiKobo, votre conseiller agricole pour le Burkina Faso. Posez-moi vos questions sur le mil, le sorgho, le maïs, le niébé, l'arachide, les sols et le climat.";

    $('#chatbot-form-btn-clear').click(function(e) {
        e.preventDefault();
        $('.chat-messages').empty();
        appendMessage(welcomeMessage, false);
    });

    $('#chatbot-form-btn-voice').click(function(e) {
        e.preventDefault();

        // Note: Using webkitSpeechRecognition for simplicity, though real-world app would use Groq/OpenAI STT
        if ('webkitSpeechRecognition' in window && !isProcessing) {
            var recognition = new webkitSpeechRecognition();
            recognition.lang = 'fr-FR'; // Use French for Burkina Faso context
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;

            var $micBtn = $('#chatbot-form-btn-voice');

            recognition.start();

            recognition.onstart = function() {
                $micBtn.addClass('listening');
            };

            recognition.onresult = function(event) {
                var speechResult = event.results[0][0].transcript;
                $('#messageText').val(speechResult);
                sendMessage();
            };

            recognition.onerror = function(event) {
                console.error('Speech recognition error:', event.error);
                alert('La saisie vocale a échoué. Veuillez taper votre question.');
            };

            recognition.onend = function() {
                $micBtn.removeClass('listening');
            };
        } else {
            alert("La saisie vocale n'est pas disponible dans ce navigateur, ou une réponse est déjà en cours. Veuillez taper votre question.");
        }
    });

    $('#voiceReadingCheckbox').change(function() {
        if (!$(this).is(':checked')) {
            stopCurrentAudio();
        }
    });

    setTimeout(function() {
        appendMessage(welcomeMessage, false);
    }, 500);
});
