$(function () {

    // ------------------------------
    // Utility: Scroll to bottom
    // ------------------------------
    function scrollToBottom() {
        const panel = document.getElementById("chatPanel");
        panel.scrollTop = panel.scrollHeight;
    }

    // ------------------------------
    // Append user/bot messages
    // ------------------------------
    function appendUser(message) {
        $("#chatPanel").append(`
            <div class="message user-message">${message}</div>
        `);
        scrollToBottom();
    }

    function appendBot(message) {
        $("#chatPanel").append(`
            <div class="message bot-message">${message}</div>
        `);
        scrollToBottom();
    }

    // ------------------------------
    // Typing Indicator
    // ------------------------------
    function showTyping() {
        $("#chatPanel").append(`
            <div class="message bot-message typing-indicator">
                <span></span><span></span><span></span>
            </div>
        `);
        scrollToBottom();
    }

    function hideTyping() {
        $(".typing-indicator").remove();
    }

    // ------------------------------
    // Input disable/enable
    // ------------------------------
    function disableInput() {
        $("#messageText").prop("disabled", true);
        $("#send-btn").prop("disabled", true);
        $("#voice-btn").prop("disabled", true);
    }

    function enableInput() {
        $("#messageText").prop("disabled", false);
        $("#send-btn").prop("disabled", false);
        $("#voice-btn").prop("disabled", false);
    }

    let isProcessing = false;

    // ------------------------------
    // SEND MESSAGE MAIN LOGIC
    // ------------------------------
    function sendMessage() {
        const message = $("#messageText").val().trim();
        if (!message || isProcessing) return;

        isProcessing = true;
        disableInput();

        appendUser(message);
        $("#messageText").val("");

        showTyping();

        $.ajax({
            type: "POST",
            url: "/ask",
            data: { message: message },
            success: function (response) {
                hideTyping();

                if (response.error) {
                    appendBot("❌ Erreur : " + response.error);
                } else {
                    appendBot(response.answer);

                    // Voice output
                    if ($("#voiceReadingCheckbox").is(":checked") && response.audio_url) {
                        const audio = new Audio(response.audio_url);
                        audio.play().catch(e => {
                            console.warn("Autoplay blocked:", e);
                        });
                    }
                }

                isProcessing = false;
                enableInput();
            },
            error: function () {
                hideTyping();
                appendBot("⚠️ Désolé, une erreur s'est produite. Veuillez réessayer.");
                isProcessing = false;
                enableInput();
            }
        });
    }

    // ------------------------------
    // Send button
    // ------------------------------
    $("#send-btn").on("click", function (e) {
        e.preventDefault();
        sendMessage();
    });

    // Press ENTER to send
    $("#messageText").on("keypress", function (e) {
        if (e.which === 13) {
            e.preventDefault();
            sendMessage();
        }
    });

    // ------------------------------
    // Voice Input (Web Speech API)
    // ------------------------------
    $("#voice-btn").on("click", function () {
        if (!("webkitSpeechRecognition" in window)) {
            alert("🎤 Votre navigateur ne supporte pas la reconnaissance vocale.");
            return;
        }

        if (isProcessing) return;

        const recognition = new webkitSpeechRecognition();
        recognition.lang = "fr-FR";
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.start();

        recognition.onresult = function (event) {
            const text = event.results[0][0].transcript;
            $("#messageText").val(text);
            sendMessage();
        };

        recognition.onerror = function () {
            alert("⚠️ Impossible d'utiliser le micro. Réessayez.");
        };
    });

    // ------------------------------
    // Clear Chat
    // ------------------------------
    $("#chatbot-form-btn-clear").on("click", function () {
        $("#chatPanel").empty();
        appendBot(welcomeMessage);
    });

    // ------------------------------
    // Welcome Message
    // ------------------------------
    const welcomeMessage =
        "🌾 Bienvenue à DakiKobo ! Je suis votre assistant agricole intelligent. Posez-moi vos questions sur les cultures du Burkina Faso.";

    setTimeout(() => appendBot(welcomeMessage), 300);
});
