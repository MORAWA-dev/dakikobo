DakiKobo: AI-Powered Agricultural Advisor for Burkina Faso 🌾

Project Overview

DakiKobo (named for "knowledge or advice farm" in local languages) is a specialized AI chatbot designed to empower smallholder farmers in Burkina Faso.

This Python web application leverages a Retrieval-Augmented Generation (RAG) architecture to provide timely, accurate, and localized advice. The bot's knowledge base is grounded in official Burkina Faso agricultural reports, regional policy documents (FAO, AGRA, WFP), and technical guides tailored to the Sahel and Sudanian Savanna zones.

The application includes Text-to-Speech (TTS) capability to ensure accessibility for users with limited literacy.

Features

Localized Knowledge Base: RAG retrieval from custom documents focusing on Burkina Faso crops (Sorghum, Millet, Niébé, Cotton).

High-Speed Inference: Uses Groq (Mixtral 8x7b) for ultra-low latency, ensuring fast, real-time responses in the chat.

Multilingual Support: Frontend is configured for French (Français), and the LLM is primed to handle regional terminology.

Voice Output (TTS): Converts text answers into spoken French audio using gtts.

Modularity: Built on a robust Flask backend with LangChain and ChromaDB for easy expansion and maintenance.

Installation and Setup (Optimized for macOS)

Follow these steps to set up the DakiKobo project locally.

Prerequisites

Python 3.10 or 3.11: Recommended versions.

Groq API Key: Obtain a key from the Groq console.

Installation Steps

STEP 1: Clone the Repository

# Assuming you already have the files

cd /path/to/AgriGenius-main

STEP 2: Create and Activate Virtual Environment

python3 -m venv dakikobo_env
source dakikobo_env/bin/activate

STEP 3: Install Dependencies (Using Flexible Fixes)

# This command installs all required packages (including the compatible versions for Mac Intel).

pip install -r requirements.txt

STEP 4: Configure API Keys and Code

Groq API Key: Open chat2.py and replace "xxxx" with your actual Groq API key.

File Placement: Place your Burkina Faso PDF documents directly inside the /Data folder.

STEP 5: Run the Flask Web Application

Ensure your (dakikobo_env) is active, and run the main application file.

python app.py

Usage

Access: Open your web browser (Chrome recommended) and navigate to http://127.0.0.1:5000 to use DakiKobo.

Query: Ask a question specific to Burkina Faso agriculture.

Voice Output: Check the "Activer la lecture vocale" box to hear DakiKobo speak the answer in French.

Technology Stack

Component

Role

Used Library/Platform

LLM Inference

High-speed answer generation

Groq (using Mixtral 8x7b)

RAG Orchestration

Pipeline for knowledge retrieval

LangChain (Core, Community)

Vector Store

Indexing and retrieval of documents

ChromaDB

Web Framework

Frontend and API routing

Flask (Python)

TTS (Voice)

Generating audio response

gTTS (Google Text-to-Speech)
Core Web/Flask

Flask==3.0.3
Werkzeug==3.0.3
Jinja2==3.1.4
itsdangerous==2.2.0

RAG/LangChain Core (Use the versions from the original project)

langchain==0.2.0
langchain-community==0.2.0
langchain-core==0.2.0

Specific RAG/LLM Connectors we are using

langchain-groq # Groq connector
langchain-text-splitters # The fix for the ModuleNotFoundError: No module named 'langchain.text_splitter'
chromadb==0.5.0
PyPDF2==3.0.1
sentence-transformers==2.7.0

Dependencies related to Scientific Computing (Flexible versions to fix Mac/Intel issues)

numpy
scipy
torch
tokenizers
transformers
safetensors
onnxruntime

Dependencies for Text-to-Speech (TTS)

gtts # For voice output

Other required packages

requests==2.31.0
Pygments
rich
openai
tiktoken
pydantic
tenacity
httpx
