# Gemini Suggestions for DakiKobo — Session 2

This session focuses on improving the quality of the RAG pipeline by upgrading the embedding model and adding source attribution to build user trust.

---

## Session 2: Improving Retrieval Quality & Source Attribution

**Goal:** Enhance retrieval accuracy for French-language queries and provide users with source citations for answer verification and trust.

### 1. Plan

1.  **Upgrade Embedding Model:** In `config.py`, replace the default `all-MiniLM-L6-v2` with a more powerful, multilingual model (`paraphrase-multilingual-mpnet-base-v2`) better suited for French.
2.  **Extract Source Documents:** In `app.py`, modify the `/ask` route to process the source documents returned by the RAG chain.
3.  **Display Sources in UI:** Update `static/js/index.js` to create a dedicated space for sources below the bot's answer and render the source filenames.
4.  **Add CSS for Sources:** Add styling in `static/css/style.css` for the new source display area to ensure it's readable and visually distinct.

### 2. Code

**A. Upgrade Embedding Model in `config.py`**

A better multilingual model will significantly improve understanding of French queries.

```diff
--- a/config.py
+++ b/config.py
@@ -16,7 +16,7 @@
 # =================================================================
 # RAG & EMBEDDING
 # =================================================================
-EMBEDDING_MODEL = "all-MiniLM-L6-v2"
+EMBEDDING_MODEL = "paraphrase-multilingual-mpnet-base-v2"
 CHUNK_SIZE = 1000
 CHUNK_OVERLAP = 100
 SIMILARITY_THRESHOLD = 0.5

```
**Note:** After changing the embedding model, you **must delete the old database** to force re-creation with the new embeddings. Run this command:
`rm -rf db/chroma_db`

**B. Return Source Documents in `app.py`**

Modify the `/ask` route to handle the `source_documents` returned by the chain and pass them to the frontend.

```diff
--- a/app.py
+++ b/app.py
@@ -46,11 +46,18 @@
 
     try:
         response = chain.invoke(query)
-        answer = response["result"]
+        answer = response.get("result", "Sorry, I could not find an answer.")
+        
+        # --- NEW: Extract and clean up source documents ---
+        source_docs = response.get("source_documents", [])
+        # Get unique source names from metadata
+        sources = sorted(list(set([doc.metadata.get("source", "Unknown") for doc in source_docs])))
+
         audio_url = text_to_speech_to_static(answer)
-        return jsonify({"answer": answer, "audio_url": audio_url})
+        
+        return jsonify({"answer": answer, "sources": sources, "audio_url": audio_url})
 
     except Exception as e:
         print(f"ERROR — LLM/RAG execution failed: {e}")
         return jsonify({
             "answer": f"Sorry, {BOT_NAME} encountered a processing error. Please check the server logs.",
+            "sources": [],
             "audio_url": "",
         })
 

```

**C. Display Sources in `static/js/index.js`**

Update the JavaScript to create and populate the sources section.

```diff
--- a/static/js/index.js
+++ b/static/js/index.js
@@ -13,7 +13,10 @@
         var messageElement = $('<div class="message-container ' + (isUser ? 'user-container' : 'bot-container') + '">' + 
                             logoHTML + 
                             '<div class="message ' + messageClass + '"></div>' +
-                            userImageHTML +
+                            userImageHTML + 
+                           '</div>' +
+                           // Add a placeholder for sources, only for bot messages
+                           (isUser ? '' : '<div class="sources-container"></div>') 
                            '</div>');
         $('.chat-messages').append(messageElement);
 
@@ -21,7 +24,7 @@
             messageElement.find('.message').text(message);
         } else {
             typeMessage(message, messageElement.find('.message'));
-        }
+        } 
 
         $('.chat-messages').scrollTop($('.chat-messages')[0].scrollHeight);
         return messageElement;
@@ -75,13 +78,22 @@
                 success: function(response) {
                     removeTypingIndicator();
                     if (response.error) {
-                        appendMessage("Error: " + response.error, false);
+                        var botMessageElement = appendMessage("Error: " + response.error, false);
                     } else {
                         var answer = response.answer;
                         var audioUrl = response.audio_url; // <-- Retrieve the audio URL from Flask
+                        var sources = response.sources;
 
                         // Append bot message 
-                        appendMessage(answer, false);
+                        var botMessageElement = appendMessage(answer, false);
+
+                        // --- NEW: Render sources ---
+                        if (sources && sources.length > 0) {
+                            var sourcesHtml = '<span>Sources:</span><ul>';
+                            sources.forEach(function(source) {
+                                sourcesHtml += '<li>' + source + '</li>';
+                            });
+                            sourcesHtml += '</ul>';
+                            botMessageElement.next('.sources-container').html(sourcesHtml);
+                        }
 
                         // --- NEW AUDIO PLAYBACK LOGIC ---
                         if ($('#voiceReadingCheckbox').is(':checked') && audioUrl) {

```

**D. Style the Sources in `static/css/style.css`**

Add these CSS rules to the end of your stylesheet.

```css
/* Append this to static/css/style.css */

.sources-container {
  font-size: 0.75rem;
  color: #888;
  margin: 8px 50px 15px 50px;
  padding-left: 15px;
  border-left: 3px solid #e0e0e0;
}

.sources-container span {
  font-weight: 500;
  color: #555;
  display: block;
  margin-bottom: 4px;
}

.sources-container ul {
  margin: 0;
  padding-left: 20px;
  list-style-type: disc;
}

.sources-container li {
  margin-bottom: 2px;
}
```

### 3. Definition of Done

1.  **Crucially, delete the old database:** `rm -rf db/chroma_db`.
2.  Start the server. It should log "Creating new ChromaDB..." as it re-indexes with the new embedding model. This will take longer than a normal startup.
3.  Ask a test question: `Comment traiter les maladies du niébé ?`
4.  The bot should respond with an answer.
5.  **Verify that below the answer, there is a "Sources:" section listing one or more PDF filenames (e.g., `csa_investment_plan_burkina_final.pdf`).**

### 4. Risks

*   **Model Download:** The first time the new embedding model is used, `sentence-transformers` will download it, which can take a few minutes and requires an internet connection.
*   **Performance:** The new embedding model is larger and may be slightly slower than the previous one, but the increase in accuracy is a worthwhile trade-off.

---
This concludes the suggestions for Session 2. Let me know when you are ready to proceed with Session 3.
