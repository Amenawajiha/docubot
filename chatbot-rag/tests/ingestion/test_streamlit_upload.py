from unittest.mock import MagicMock, mock_open, patch

from src.ingestion.streamlit_upload import (
    display_upload_section,
    format_file_size,
    log_upload_to_file,
)


def test_format_file_size_units_and_boundaries():
    assert format_file_size(0) == "0.00 B"
    assert format_file_size(1023) == "1023.00 B"
    assert format_file_size(1024) == "1.00 KB"
    assert format_file_size(1024 * 1024) == "1.00 MB"
    assert format_file_size(1024 * 1024 * 1024) == "1.00 GB"


def test_log_upload_to_file_success_no_existing_log():
    m = mock_open()
    with patch("src.ingestion.streamlit_upload.get_config", return_value="fake.log"):
        with patch("src.ingestion.streamlit_upload.Path.exists", return_value=False):
            with patch("builtins.open", m):
                with patch("src.ingestion.streamlit_upload.datetime") as dt:
                    dt.now.return_value.strftime.return_value = "2026-01-09 10:00:00"
                    log_upload_to_file("a.docx", "success", file_size=1024)

    handle = m()
    written = "".join(call.args[0] for call in handle.write.call_args_list)
    assert "SUCCESS: a.docx" in written
    assert "1.00 KB" in written


def test_log_upload_to_file_failed_with_existing_lines_filters_duplicates():
    m = mock_open(read_data="[t] SUCCESS: a.docx | Size: 1.00 KB\n[t] SUCCESS: b.docx | Size: 2.00 KB\n")
    with patch("src.ingestion.streamlit_upload.get_config", return_value="fake.log"):
        with patch("src.ingestion.streamlit_upload.Path.exists", return_value=True):
            with patch("builtins.open", m):
                with patch("src.ingestion.streamlit_upload.datetime") as dt:
                    dt.now.return_value.strftime.return_value = "2026-01-09 11:00:00"
                    log_upload_to_file("a.docx", "failed", error_msg="bad")

    handle = m()
    # writelines gets filtered lines without old a.docx
    writelines_arg = handle.writelines.call_args[0][0]
    joined_old = "".join(writelines_arg)
    assert "a.docx" not in joined_old
    assert "b.docx" in joined_old

    new_entry = "".join(call.args[0] for call in handle.write.call_args_list)
    assert "FAILED: a.docx - Error: bad" in new_entry


class _FakeStatus:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def update(self, **kwargs):
        return None


def _patch_streamlit_common(uploaded_file=None, button=False):
    patches = [
        patch("src.ingestion.streamlit_upload.st.markdown"),
        patch("src.ingestion.streamlit_upload.st.file_uploader", return_value=uploaded_file),
        patch("src.ingestion.streamlit_upload.st.button", return_value=button),
        patch("src.ingestion.streamlit_upload.st.info"),
        patch("src.ingestion.streamlit_upload.st.warning"),
        patch("src.ingestion.streamlit_upload.st.success"),
        patch("src.ingestion.streamlit_upload.st.error"),
        patch("src.ingestion.streamlit_upload.st.rerun"),
        patch("src.ingestion.streamlit_upload.st.status", return_value=_FakeStatus()),
    ]
    return patches


def test_display_upload_section_no_file_selected_shows_hint():
    patches = _patch_streamlit_common(uploaded_file=None, button=False)
    with patches[0], patches[1], patches[2], patches[3] as info, patches[4], patches[5], patches[6], patches[7], patches[8]:
        display_upload_section(loader=MagicMock())
    assert any(
         ("upload" in str(c).lower()) and ("file" in str(c).lower())
         for c in info.call_args_list
     )


def test_display_upload_section_file_selected_button_not_clicked():
    up = MagicMock()
    up.name = "x.docx"
    up.getvalue.return_value = b"abc"
    patches = _patch_streamlit_common(uploaded_file=up, button=False)
    with patches[0], patches[1], patches[2], patches[3] as info, patches[4], patches[5], patches[6], patches[7], patches[8]:
        display_upload_section(loader=MagicMock())
    assert any("x.docx" in str(c) for c in info.call_args_list)


def test_display_upload_section_success_replaced_flow():
    up = MagicMock()
    up.name = "x.docx"
    up.getvalue.return_value = b"abc"
    loader = MagicMock()
    loader.process_document.return_value = {
        "status": "success",
        "was_replaced": True,
        "old_chunk_count": 2,
        "chunks_created": 3,
    }

    patches = _patch_streamlit_common(uploaded_file=up, button=True)
    with patch("src.ingestion.streamlit_upload.log_upload_to_file") as logf:
        with patches[0], patches[1], patches[2], patches[3], patches[4] as warning, patches[5], patches[6], patches[7] as rerun, patches[8]:
            display_upload_section(loader=loader)

    loader.process_document.assert_called_once_with(b"abc", "x.docx")
    logf.assert_called_once_with("x.docx", "success", file_size=3)
    warning.assert_called_once()
    rerun.assert_called_once()


def test_display_upload_section_success_new_doc_flow():
    up = MagicMock()
    up.name = "x.docx"
    up.getvalue.return_value = b"abc"
    loader = MagicMock()
    loader.process_document.return_value = {"status": "success", "was_replaced": False, "chunks_created": 3}

    patches = _patch_streamlit_common(uploaded_file=up, button=True)
    with patch("src.ingestion.streamlit_upload.log_upload_to_file"):
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5] as success, patches[6], patches[7], patches[8]:
            display_upload_section(loader=loader)
    success.assert_called_once()


def test_display_upload_section_error_flow_logs_failed():
    up = MagicMock()
    up.name = "x.docx"
    up.getvalue.return_value = b"abc"
    loader = MagicMock()
    loader.process_document.return_value = {"status": "error", "error": "pipeline failed"}

    patches = _patch_streamlit_common(uploaded_file=up, button=True)
    with patch("src.ingestion.streamlit_upload.log_upload_to_file") as logf:
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6] as err, patches[7], patches[8]:
            display_upload_section(loader=loader)

    err.assert_called_once()
    logf.assert_called_once_with("x.docx", "failed", error_msg="pipeline failed")
