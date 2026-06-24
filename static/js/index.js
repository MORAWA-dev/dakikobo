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

    function appendMessage(message, isUser) {
        var messageClass = isUser ? 'user-message' : 'bot-message';
        // Updated logo reference to DakiKobo
        var logoHTML = isUser ? '' : '<div class="bot-logo"><img src="/static/robo.png" alt="DakiKobo Logo"></div>';
        var userImageHTML = isUser ? '<div class="user-image"><img src="/static/user.png" alt="User"></div>' : '';
        var messageElement = $('<div class="message-container ' + (isUser ? 'user-container' : 'bot-container') + '">' + 
                            logoHTML + 
                            '<div class="message ' + messageClass + '"></div>' +
                            userImageHTML +
                           '</div>');
        $('.chat-messages').append(messageElement);

        if (isUser) {
            messageElement.find('.message').text(message);
        } else {
            typeMessage(message, messageElement.find('.message'));
        }

        $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
        return messageElement;
    }

    function typeMessage(message, element, speed = 15) {
        let i = 0;
        element.html('');
        const typingInterval = setInterval(() => {
            if (i < message.length) {
                element.html(element.html() + message.charAt(i));
                i++;
            } else {
                clearInterval(typingInterval);
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
    }

    function enableInput() {
        $('#messageText').prop('disabled', false);
        $('#chatbot-form-btn').prop('disabled', false);
        $('#chatbot-form-btn-voice').prop('disabled', false);
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

                        // Append bot message 
                        appendMessage(answer, false);

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

    // Updated welcome message to DakiKobo and French
    var welcomeMessage = "🌾 Bienvenue à DakiKobo ! 💡 I'm DakiKobo, your expert advisor for agriculture in Burkina Faso. Ask me anything about millet, cowpea, or local soil and climate!";

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

            recognition.start();

            recognition.onresult = function(event) {
                var speechResult = event.results[0][0].transcript;
                $('#messageText').val(speechResult);
                sendMessage();
            };

            recognition.onerror = function(event) {
                console.error('Speech recognition error:', event.error);
                alert('Voice input failed. Please try typing your question.');
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