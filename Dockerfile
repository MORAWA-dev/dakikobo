FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV HF_HOME=/home/user/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/home/user/.cache/sentence-transformers

RUN useradd -m -u 1000 user
ENV PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app
RUN chown -R user:user /home/user/app

USER user

COPY --chown=user:user requirements.txt .
RUN python -m pip install --user --no-cache-dir -r requirements.txt

COPY --chown=user:user . .

EXPOSE 7860

CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-7860} --workers 1 --timeout 180"]
