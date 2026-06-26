$(function() {
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

    function appendMessage(message, isUser, sources, question) {
        var messageClass = isUser ? 'user-message' : 'bot-message';
        // Updated logo reference to DakiKobo
        var logoHTML = isUser ? '' : '<div class="bot-logo"><img src="/static/images/bot_avatar.png" alt="DakiKobo Logo"></div>';
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
                renderSources(bubble, sources);
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

    function renderSources(bubble, sources) {
        if (!sources || sources.length === 0) {
            return;
        }
        var $box = $('<div class="sources"></div>');
        $box.append($('<span class="sources-label"></span>').text('Sources :'));
        sources.forEach(function(src) {
            $box.append($('<span class="source-chip"></span>').text(src));
        });
        bubble.append($box);
        $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
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

    // Quick-action chips: tap a French chip to ask that question.
    $('.quick-chips').on('click', '.chip', function(e) {
        e.preventDefault();
        if (isProcessing) {
            return;
        }
        var question = $(this).data('question');
        $('#messageText').val(question);
        sendMessage();
    });

    $('#messageText').keypress(function(e) {
        if (e.which == 13) {
            e.preventDefault();
            sendMessage();
        }
    });

    var isProcessing = false;

    function disableInput() {
        $('#messageText').prop('disabled', true);
        $('#chatbot-form-btn').prop('disabled', true);
        $('#chatbot-form-btn-voice').prop('disabled', true);
        $('#chatbot-form-btn-image').prop('disabled', true);
    }

    function enableInput() {
        $('#messageText').prop('disabled', false);
        $('#chatbot-form-btn').prop('disabled', false);
        $('#chatbot-form-btn-voice').prop('disabled', false);
        $('#chatbot-form-btn-image').prop('disabled', false);
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
                        appendMessage("Error: " + response.error, false);
                    } else {
                        var answer = response.answer;
                        var audioUrl = response.audio_url; // <-- Retrieve the audio URL from Flask
                        var sources = response.sources;    // <-- Source filenames from RAG

                        // Append bot message (with source chips + feedback)
                        appendMessage(answer, false, sources, message);

                        // --- NEW AUDIO PLAYBACK LOGIC ---
                        if ($('#voiceReadingCheckbox').is(':checked') && audioUrl) {
                            var player = new Audio(audioUrl);
                            player.play().catch(e => {
                                console.error("Audio playback error (usually due to browser autoplay restrictions):", e);
                            });
                        }
                    }
                    isProcessing = false;
                    enableInput();
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    removeTypingIndicator();
                    console.log(errorThrown);
                    appendMessage("Sorry, there was an error processing your request. Please try again later.", false);
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
        };
        reader.readAsDataURL(file);

        var formData = new FormData();
        formData.append('image', file);
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
                    appendMessage("Erreur : " + response.error, false);
                } else {
                    appendMessage(response.answer, false, response.sources);
                    if ($('#voiceReadingCheckbox').is(':checked') && response.audio_url) {
                        new Audio(response.audio_url).play().catch(function(err) {
                            console.error("Audio playback error:", err);
                        });
                    }
                }
                isProcessing = false;
                enableInput();
            },
            error: function() {
                removeTypingIndicator();
                appendMessage("Désolé, l'analyse de l'image a échoué. Veuillez réessayer.", false);
                isProcessing = false;
                enableInput();
            }
        });
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
            alert('Speech recognition is not supported in this browser or processing is in progress. Try typing.');
        }
    });

    $('#voiceReadingCheckbox').change(function() {
        if (!$(this).is(':checked')) {
            // Stop any currently speaking TTS audio if unchecked
            if (synth.speaking) {
                synth.cancel();
            }
        }
    });

    setTimeout(function() {
        appendMessage(welcomeMessage, false);
    }, 500);
});