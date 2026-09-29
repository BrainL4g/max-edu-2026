"""Тесты извлечения текста из загруженных файлов резюме."""

from __future__ import annotations

import io

import pytest

from backend.app.core.exceptions import InvalidDataError
from backend.app.services.resume_text import MAX_RESUME_BYTES, extract_resume_text


def _docx_bytes() -> bytes:
    """Валидный DOCX с одним абзацем (собирается тем же python-docx)."""
    from docx import Document

    document = Document()
    document.add_paragraph("Python разработчик")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _pdf_with_text() -> bytes:
    """Минимальный PDF с текстовым слоем (собирается вручную)."""
    stream = b"BT /F1 12 Tf 40 700 Td (Python developer) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    out += trailer.encode()
    return bytes(out)


def _docx_with_table() -> bytes:
    """DOCX с абзацем и таблицей."""
    from docx import Document

    document = Document()
    document.add_paragraph("Опыт: 3 года")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Python"
    table.rows[0].cells[1].text = "SQL"
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_plain_utf8_text() -> None:
    assert extract_resume_text("cv.txt", b"Python, SQL") == "Python, SQL"


def test_text_without_extension() -> None:
    assert extract_resume_text(None, b"Python") == "Python"


def test_other_text_extensions() -> None:
    for name in ("cv.md", "cv.rtf", "data.json", "page.html"):
        assert extract_resume_text(name, b"content") == "content"


def test_strips_surrounding_whitespace() -> None:
    assert extract_resume_text("cv.txt", b"  \n Python \n ") == "Python"


def test_empty_file_rejected() -> None:
    with pytest.raises(InvalidDataError, match="пустой"):
        extract_resume_text("cv.txt", b"")


def test_oversized_file_rejected() -> None:
    with pytest.raises(InvalidDataError, match="слишком большой"):
        extract_resume_text("cv.txt", b"x" * (MAX_RESUME_BYTES + 1))


def test_unsupported_extension_rejected() -> None:
    with pytest.raises(InvalidDataError, match="не поддерживается"):
        extract_resume_text("photo.png", b"\x89PNG")


def test_blank_text_rejected() -> None:
    with pytest.raises(InvalidDataError, match="не нашлось текста"):
        extract_resume_text("cv.txt", b"   \n  ")


def test_docx_text_is_extracted() -> None:
    assert "Python разработчик" in extract_resume_text("cv.docx", _docx_bytes())


def test_docx_table_cells_are_extracted() -> None:
    """Табличная часть резюме тоже попадает в текст."""
    text = extract_resume_text("cv.docx", _docx_with_table())
    assert "Опыт: 3 года" in text
    assert "Python | SQL" in text


def test_pdf_text_is_extracted() -> None:
    assert "Python developer" in extract_resume_text("cv.pdf", _pdf_with_text())


def test_docx_broken_rejected() -> None:
    with pytest.raises(InvalidDataError, match="Не удалось прочитать DOCX"):
        extract_resume_text("cv.docx", b"not a zip archive")


def test_pdf_without_text_layer_rejected() -> None:
    with pytest.raises(InvalidDataError, match="Не удалось прочитать PDF|текста"):
        extract_resume_text("cv.pdf", b"%PDF-1.4\nbroken")
