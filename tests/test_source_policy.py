import json
from core.rag_pipeline import list_markdown_files, list_pdf_files, load_markdown_from_folder


def test_pending_missing_and_approved_sources(tmp_path):
    for status in ['reviewed_by_owner', 'reviewed_by_codex_pending_human_review', 'missing']:
        (tmp_path / (status+'.md')).write_text(f'---\ntitle: Guide\nsource_file: guide.pdf\nreview_status: {status}\n---\nConseil')
    assert [p.rsplit('/',1)[-1] for p in list_markdown_files(str(tmp_path))] == ['reviewed_by_owner.md']
    assert len(load_markdown_from_folder(str(tmp_path))) == 1


def test_pdf_fallback_requires_approved_sidecar(tmp_path):
    pdf = tmp_path/'guide.pdf'
    pdf.write_bytes(b'%PDF-test')
    assert list_pdf_files(str(tmp_path)) == []
    pdf.with_suffix('.pdf.review.json').write_text(json.dumps({'title':'Guide', 'source_file':'guide.pdf', 'review_status':'reviewed_by_owner'}))
    assert list_pdf_files(str(tmp_path)) == [str(pdf)]
