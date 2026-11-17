"""Quality, masking, OCR, and the process endpoint. Supabase is mocked."""

import io
import logging
from datetime import date, datetime, timedelta, timezone

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.config import settings
from app.main import app
from app.processing.loader import DocumentUnreadableError, load_document
from app.processing.masking import check_id_numbers, extract_masked_id_suffixes, mask_sensitive, verhoeff_checksum
from app.processing.ocr import run_ocr
from app.processing.pipeline import process_document
from app.processing.preprocess import prepare_for_ocr, threshold_for_ocr
from app.processing.quality import measure_quality
from fastapi.testclient import TestClient
from tests.test_auth import _token
from tests.test_documents import APP_ID, UPLOAD_ID, _auth, _cleared_shared_results, _install
from tests.test_documents import Store

client = TestClient(app)
SECRET_PATH = "secret/do-not-return.jpg"


@pytest.fixture(autouse=True)
def _restore_pillow_limit():
    # One loader test lowers Pillow's bomb limit. Put the normal limit back afterwards.
    yield
    Image.MAX_IMAGE_PIXELS = settings.OCR_MAX_PIXELS


def _font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for path in (
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _text_image(words: str, size: tuple[int, int] = (1400, 320)) -> np.ndarray:
    picture = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(picture)
    draw.text((40, 90), words, fill="black", font=_font(72))
    return cv2.cvtColor(np.asarray(picture), cv2.COLOR_RGB2BGR)


def _png_bytes() -> bytes:
    picture = Image.new("RGB", (40, 30), "white")
    buffer = io.BytesIO()
    picture.save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_bytes() -> bytes:
    picture = Image.new("RGB", (40, 30), "white")
    buffer = io.BytesIO()
    picture.save(buffer, format="JPEG")
    return buffer.getvalue()


def _pdf_bytes(pages: int) -> bytes:
    pictures = [Image.new("RGB", (80, 60), "white") for _ in range(pages)]
    buffer = io.BytesIO()
    pictures[0].save(buffer, format="PDF", save_all=True, append_images=pictures[1:])
    return buffer.getvalue()


def _tesseract_ready() -> bool:
    import pytesseract

    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def test_sharp_image_scores_higher_than_a_blurred_copy() -> None:
    sharp = _text_image("SHARP TEXT LINE")
    blurred = cv2.GaussianBlur(sharp, (31, 31), 0)
    assert measure_quality(sharp)["blur_score"] > measure_quality(blurred)["blur_score"]


def test_dark_image_is_less_bright_than_a_light_one() -> None:
    dark = np.full((80, 80, 3), 20, dtype=np.uint8)
    bright = np.full((80, 80, 3), 230, dtype=np.uint8)
    assert measure_quality(dark)["brightness_mean"] < measure_quality(bright)["brightness_mean"]


def test_rotated_text_reports_a_tilt() -> None:
    base = Image.new("RGB", (640, 180), "white")
    ImageDraw.Draw(base).rectangle((30, 70, 600, 110), fill="black")
    rotated = base.rotate(18, expand=True, fillcolor="white")
    image = cv2.cvtColor(np.asarray(rotated), cv2.COLOR_RGB2BGR)
    angle = float(measure_quality(image)["skew_angle_degrees"])
    assert angle != 0


def test_blank_page_and_size() -> None:
    blank = np.full((100, 200, 3), 255, dtype=np.uint8)
    metrics = measure_quality(blank)
    assert metrics["is_probably_blank"] is True
    assert metrics["width"] == 200
    assert metrics["height"] == 100


def test_masking_hides_ids_and_leaves_everyday_numbers() -> None:
    spaced, count = mask_sensitive("Aadhaar 1234 5678 9012")
    assert spaced == "Aadhaar XXXX XXXX 9012"
    assert count == 1
    plain, _count = mask_sensitive("Aadhaar 123456789012")
    assert plain == "Aadhaar XXXX XXXX 9012"
    hyphen, _count = mask_sensitive("Aadhaar 1234-5678-9012")
    assert hyphen == "Aadhaar XXXX XXXX 9012"

    tamil, tamil_count = mask_sensitive("எண் ௧௨௩௪ ௫௬௭௮ ௯௦௧௨")
    assert tamil == "எண் XXXX XXXX 9012"
    assert tamil_count == 1

    vid, vid_count = mask_sensitive("VID 1234 5678 9012 3456")
    assert vid == "VID XXXX XXXX XXXX 3456"
    assert vid_count == 1

    phone = "Call 9876543210 today"
    dated = "Born 12/05/2003"
    pin = "PIN 600001"
    for sample in (phone, dated, pin):
        masked, sample_count = mask_sensitive(sample)
        assert masked == sample
        assert sample_count == 0

    suffixes = extract_masked_id_suffixes("Aadhaar 1234 5678 9012 and VID 1234123412341234")
    assert suffixes == ["9012", "1234"]
    assert all(len(item) == 4 for item in suffixes)
    assert "123456789012" not in suffixes
    assert extract_masked_id_suffixes("XXXX XXXX 9012") == ["9012"]


def test_id_checksum_reports_last4_only() -> None:
    # Independent Verhoeff tables, so this test does not trust the app's copy.
    multiplication = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
        (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
        (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
        (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
        (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
        (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
        (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
        (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
        (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
    )
    permutation = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
        (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
        (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
        (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
        (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
        (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
        (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
    )
    inverse = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)

    def checksum(number: str) -> int:
        check = 0
        for index, char in enumerate(reversed(number)):
            check = multiplication[check][permutation[index % 8][int(char)]]
        return check

    body = "23456789012"
    valid = body + str(inverse[checksum(body + "0")])
    changed = valid[:5] + ("0" if valid[5] != "0" else "1") + valid[6:]
    good = check_id_numbers(valid)
    bad = check_id_numbers(changed)
    assert good == [{"type": "aadhaar", "last4": valid[-4:], "checksum_valid": True}]
    assert bad[0]["checksum_valid"] is False
    assert valid not in str(good)
    assert changed not in str(bad)
    assert verhoeff_checksum(valid) == 0


def test_masking_covers_line_breaks_adjacent_ids_and_mixed_text() -> None:
    def once(source: str) -> str:
        masked, _count = mask_sensitive(source)
        again, again_count = mask_sensitive(masked)
        assert again == masked
        assert again_count == 0
        return masked

    assert once("123456789012") == "XXXX XXXX 9012"
    assert once("1234 5678 9012") == "XXXX XXXX 9012"
    assert once("1234-5678-9012") == "XXXX XXXX 9012"
    assert once("1234\n5678\n9012") == "XXXX XXXX 9012"
    assert once("1234\r\n5678\r\n9012") == "XXXX XXXX 9012"

    assert once("1234567890123456") == "XXXX XXXX XXXX 3456"
    assert once("1234 5678 9012 3456") == "XXXX XXXX XXXX 3456"
    assert once("1234-5678-9012-3456") == "XXXX XXXX XXXX 3456"
    assert once("1234\n5678\n9012\n3456") == "XXXX XXXX XXXX 3456"

    assert once("9876543210") == "9876543210"
    assert once("17-11-2026") == "17-11-2026"
    assert once("12/05/2003") == "12/05/2003"
    assert once("600001") == "600001"
    assert once("எண் ௧௨௩௪\n௫௬௭௮\n௯௦௧௨") == "எண் XXXX XXXX 9012"

    adjacent, adjacent_count = mask_sensitive("1234 5678 9012 1234 5678 9012 3456")
    assert adjacent == "XXXX XXXX 9012 XXXX XXXX XXXX 3456"
    assert adjacent_count == 2
    split_lines, split_count = mask_sensitive("1234\n5678\n9012\n1234\n5678\n9012\n3456")
    assert split_lines == "XXXX XXXX 9012\nXXXX XXXX XXXX 3456"
    assert split_count == 2
    assert once("1234 5678 9012 3456 2345 6789 0123 4567") == "XXXX XXXX XXXX 3456 XXXX XXXX XXXX 4567"
    assert once("1234\n5678\n9012\n3456\n2345\n6789\n0123\n4567") == "XXXX XXXX XXXX 3456\nXXXX XXXX XXXX 4567"

    mixed = "\n".join(
        [
            "Dummy 12-digit ID: 1234 5678 9012",
            "Dummy 16-digit VID: 1234 5678 9012 3456",
            "Dummy phone number: 9876543210",
            "Document date: 17-11-2026",
            "PIN code: 600001",
        ]
    )
    result = once(mixed)
    assert "XXXX XXXX 9012" in result
    assert "XXXX XXXX XXXX 3456" in result
    assert "9876543210" in result
    assert "17-11-2026" in result
    assert "600001" in result
    assert "1234 5678" not in result


def test_loader_reads_png_jpeg_and_pdf_and_rejects_garbage(monkeypatch: pytest.MonkeyPatch) -> None:
    png = load_document(_png_bytes(), "image/png")
    jpeg = load_document(_jpeg_bytes(), "image/jpeg")
    assert png.page_count == 1
    assert jpeg.images[0].shape[0] == 30
    pdf = load_document(_pdf_bytes(3), "application/pdf")
    assert pdf.page_count == 3
    assert len(pdf.images) == settings.OCR_MAX_PDF_PAGES
    with pytest.raises(DocumentUnreadableError):
        load_document(b"this is not a document", "application/pdf")
    monkeypatch.setattr(settings, "OCR_MAX_PIXELS", 100)
    with pytest.raises(DocumentUnreadableError):
        load_document(_png_bytes(), "image/png")


def test_prepare_for_ocr_returns_grayscale() -> None:
    image = _text_image("Hello")
    prepared = prepare_for_ocr(image, 0)
    assert prepared.ndim == 2
    binary = threshold_for_ocr(prepared)
    assert binary.shape == prepared.shape


def _form_pdf(rows: list[tuple[str, str]], *, table: bool) -> bytes:
    """A one-page A4 form. Tests use this instead of a stored sample file."""
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 28)
    image = Image.new("RGB", (1654, 2339), "white")
    draw = ImageDraw.Draw(image)
    top = 180
    for label, value in rows:
        if table:
            draw.rectangle((100, top, 1550, top + 90), outline="black", width=2)
            draw.line((700, top, 700, top + 90), fill="black", width=2)
            draw.text((120, top + 25), f"{label}:", font=font, fill="black")
            draw.text((740, top + 25), value, font=font, fill="black")
        else:
            draw.text((120, top), f"{label}: {value}", font=font, fill="black")
        top += 110
    buffer = io.BytesIO()
    image.save(buffer, format="PDF", resolution=200)
    return buffer.getvalue()


@pytest.mark.skipif(not _tesseract_ready(), reason="tesseract is not installed")
def test_form_pdf_keeps_name_date_and_address(caplog: pytest.LogCaptureFixture) -> None:
    forms = [
        (
            False,
            [
                ("Full Name", "Ravi Kumar"),
                ("Address", "8, Lake Road, Example Nagar"),
                ("Document Date", "02-03-2024"),
                ("Reference", "2345 6789 0123"),
            ],
            "RAVI KUMAR",
            date(2024, 3, 2),
            "Lake Road",
        ),
        (
            True,
            [
                ("Full Name", "Mohan Das"),
                ("Address", "4, Hill Road, Example Nagar"),
                ("Document Date", "29.08.2025"),
                ("Reference", "3456 7890 1234"),
            ],
            "MOHAN DAS",
            date(2025, 8, 29),
            "Hill Road",
        ),
    ]
    from app.validation.text_extract import extract_dates, extract_name_candidate

    for table, rows, name, issued, street in forms:
        pdf = _form_pdf(rows, table=table)
        with caplog.at_level(logging.INFO):
            result = process_document(pdf, "application/pdf")
        masked = str(result["ocr_text_masked"])
        assert extract_name_candidate(masked) == name
        assert issued in extract_dates(masked)
        assert street in masked
        assert "2345 6789" not in masked
        assert "3456 7890" not in masked
        assert name.title() not in caplog.text
        assert "2345 6789" not in caplog.text
        assert "3456 7890" not in caplog.text


@pytest.mark.skipif(not _tesseract_ready(), reason="tesseract is not installed")
def test_ocr_reads_clear_english_and_blank_page() -> None:
    read = run_ocr(_text_image("HELLO CITIZEN"), "eng")
    assert "HELLO" in str(read["text"])
    assert "CITIZEN" in str(read["text"])
    blank = run_ocr(np.full((200, 400), 255, dtype=np.uint8), "eng")
    assert blank["text"] == ""
    assert blank["word_count"] == 0


@pytest.mark.skipif(not _tesseract_ready(), reason="tesseract is not installed")
def test_pipeline_masks_a_number_in_the_image(caplog: pytest.LogCaptureFixture) -> None:
    image = _text_image("Aadhaar 1234 5678 9012")
    buffer = io.BytesIO()
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb).save(buffer, format="PNG")
    with caplog.at_level(logging.INFO):
        result = process_document(buffer.getvalue(), "image/png")
    masked = str(result["ocr_text_masked"])
    assert "XXXX XXXX 9012" in masked
    assert "1234 5678" not in masked
    assert "1234 5678" not in caplog.text
    assert "123456789012" not in caplog.text
    checks = result["quality_metrics"]["id_checks"]
    assert isinstance(checks, list)
    assert all(len(str(item["last4"])) == 4 for item in checks)
    assert "123456789012" not in str(checks)


def _row(**extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": UPLOAD_ID,
        "user_id": "11111111-1111-1111-1111-111111111111",
        "storage_path": SECRET_PATH,
        "mime_type": "image/png",
        "status": "uploaded",
        "quality_metrics": {},
        "ocr_text_masked": None,
        "updated_at": "2020-01-01T00:00:00+00:00",
    }
    row.update(extra)
    return row


def _patch_pipeline(monkeypatch: pytest.MonkeyPatch, store: Store, outcome: object) -> dict[str, int]:
    _install(monkeypatch, store)
    seen = {"downloads": 0}

    def download(path: str) -> bytes:
        assert path == SECRET_PATH
        seen["downloads"] += 1
        return b"png"

    def fake_process(content: bytes, mime_type: str) -> dict[str, object]:
        del content, mime_type
        if isinstance(outcome, Exception):
            raise outcome
        assert isinstance(outcome, dict)
        return outcome

    monkeypatch.setattr("app.routers.documents.download_object", download)
    monkeypatch.setattr("app.routers.documents.process_document", fake_process)
    return seen


def test_process_and_result_require_a_token() -> None:
    assert client.post(f"/documents/{UPLOAD_ID}/process").status_code == 401
    assert client.get(f"/documents/{UPLOAD_ID}/result").status_code == 401


def test_another_user_cannot_process_or_read(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store()
    store.row = _row()
    _install(monkeypatch, store)
    stranger = {"Authorization": f"Bearer {_token({'sub': '99999999-9999-9999-9999-999999999999'})}"}
    assert client.post(f"/documents/{UPLOAD_ID}/process", headers=stranger).status_code == 404
    assert client.get(f"/documents/{UPLOAD_ID}/result", headers=stranger).status_code == 404


def test_process_saves_masked_text(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    store = Store()
    store.row = _row(application_id=APP_ID)
    _patch_pipeline(
        monkeypatch,
        store,
        {"quality_metrics": {"blur_score": 12}, "ocr_text_masked": "LEAKME 1234 5678 9012"},
    )
    with caplog.at_level(logging.INFO):
        response = client.post(f"/documents/{UPLOAD_ID}/process", headers=_auth())
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "processed"
    assert body["ocr_text_masked"] == "LEAKME XXXX XXXX 9012"
    assert "1234 5678" not in response.text
    assert "storage_path" not in body
    assert SECRET_PATH not in response.text
    assert store.row is not None
    assert store.row["status"] == "processed"
    assert store.row["ocr_text_masked"] == "LEAKME XXXX XXXX 9012"
    assert store.row["extracted_fields"] == {}
    assert store.row["quality_metrics"] == {"blur_score": 12}
    assert "LEAKME" not in caplog.text
    assert _cleared_shared_results(store)
    assert "1234 5678" not in caplog.text
    assert SECRET_PATH not in caplog.text


def test_process_failure_stores_a_friendly_error(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store()
    store.row = _row()
    _patch_pipeline(monkeypatch, store, RuntimeError("RAW OCR 1234 5678 9012"))
    response = client.post(f"/documents/{UPLOAD_ID}/process", headers=_auth())
    assert response.status_code == 422
    assert "1234 5678" not in response.text
    assert "clearer photo" in response.json()["detail"]
    assert store.row is not None
    assert store.row["status"] == "failed"
    assert store.row["quality_metrics"] == {"error": "We could not read this document. Please try a clearer photo."}
    assert "storage_path" not in response.json()


def test_fresh_processing_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store()
    store.row = _row(status="processing", updated_at=datetime.now(timezone.utc).isoformat())
    seen = _patch_pipeline(monkeypatch, store, {"quality_metrics": {}, "ocr_text_masked": ""})
    response = client.post(f"/documents/{UPLOAD_ID}/process", headers=_auth())
    assert response.status_code == 409
    assert response.json()["detail"] == "Already processing"
    assert seen["downloads"] == 0


def test_stale_processing_can_run_again(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store()
    stale = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    store.row = _row(status="processing", updated_at=stale)
    _patch_pipeline(monkeypatch, store, {"quality_metrics": {"blur_score": 1}, "ocr_text_masked": "done"})
    response = client.post(f"/documents/{UPLOAD_ID}/process", headers=_auth())
    assert response.status_code == 200
    assert store.row is not None
    assert store.row["status"] == "processed"


def test_result_hides_the_storage_path(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store()
    store.row = _row(status="processed", quality_metrics={"blur_score": 4}, ocr_text_masked="XXXX XXXX 9012")
    _install(monkeypatch, store)
    response = client.get(f"/documents/{UPLOAD_ID}/result", headers=_auth())
    body = response.json()
    assert response.status_code == 200
    assert body["ocr_text_masked"] == "XXXX XXXX 9012"
    assert body["quality_metrics"] == {"blur_score": 4}
    assert "storage_path" not in body
    assert SECRET_PATH not in response.text
