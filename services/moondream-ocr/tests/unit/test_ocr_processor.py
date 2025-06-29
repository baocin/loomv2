"""Unit tests for the MoondreamOCR processor class."""

import base64
from unittest.mock import MagicMock, patch
from io import BytesIO

import pytest
from PIL import Image

from app.main import MoondreamOCR
from tests.test_helpers import create_test_image_base64


@pytest.fixture
def mock_torch():
    """Mock torch module."""
    with patch("app.main.torch") as mock:
        mock.cuda.is_available.return_value = False
        mock.float32 = "float32"
        mock.float16 = "float16"
        yield mock


@pytest.fixture
def mock_transformers():
    """Mock transformers module."""
    with patch("app.main.AutoModelForCausalLM") as mock_model, patch(
        "app.main.AutoTokenizer"
    ) as mock_tokenizer:
        yield {"model": mock_model, "tokenizer": mock_tokenizer}


@pytest.fixture
def ocr_processor(mock_torch, mock_transformers):
    """Create OCR processor with mocked dependencies."""
    processor = MoondreamOCR()
    processor.model = MagicMock()
    processor.tokenizer = MagicMock()
    processor.device = "cpu"
    return processor


class TestMoondreamOCR:
    """Test MoondreamOCR class functionality."""

    def test_init_cpu_device(self, mock_torch):
        """Test initialization defaults to CPU when CUDA unavailable."""
        mock_torch.cuda.is_available.return_value = False

        processor = MoondreamOCR()

        assert processor.device == "cpu"
        assert processor.model is None
        assert processor.tokenizer is None

    def test_init_cuda_device(self, mock_torch):
        """Test initialization uses CUDA when available."""
        mock_torch.cuda.is_available.return_value = True

        processor = MoondreamOCR()

        assert processor.device == "cuda"

    @patch("app.main.os.environ")
    def test_model_cache_directory_default(self, mock_environ, mock_torch):
        """Test default model cache directory."""
        mock_environ.get.return_value = None

        processor = MoondreamOCR()

        assert "/.loom/moondream" in str(processor.model_cache_dir)

    @patch("app.main.os.environ")
    def test_model_cache_directory_custom(self, mock_environ, mock_torch):
        """Test custom model cache directory."""
        mock_environ.get.return_value = "/custom/cache"

        processor = MoondreamOCR()

        assert "/custom/cache" in str(processor.model_cache_dir)

    def test_load_model_cpu(self, mock_torch, mock_transformers):
        """Test model loading for CPU."""
        mock_torch.cuda.is_available.return_value = False
        mock_model_instance = MagicMock()
        mock_tokenizer_instance = MagicMock()
        mock_transformers["model"].from_pretrained.return_value = mock_model_instance
        mock_transformers["tokenizer"].from_pretrained.return_value = (
            mock_tokenizer_instance
        )

        processor = MoondreamOCR()
        processor.load_model()

        assert processor.model == mock_model_instance
        assert processor.tokenizer == mock_tokenizer_instance
        mock_model_instance.eval.assert_called_once()

    def test_load_model_cuda(self, mock_torch, mock_transformers):
        """Test model loading for CUDA."""
        mock_torch.cuda.is_available.return_value = True
        mock_model_instance = MagicMock()
        mock_tokenizer_instance = MagicMock()
        mock_transformers["model"].from_pretrained.return_value = mock_model_instance
        mock_transformers["tokenizer"].from_pretrained.return_value = (
            mock_tokenizer_instance
        )

        processor = MoondreamOCR()
        processor.device = "cuda"
        processor.load_model()

        mock_model_instance.to.assert_called_with("cuda")
        mock_model_instance.eval.assert_called_once()

    def test_process_image_success(self, ocr_processor):
        """Test successful image processing."""
        # Mock model responses
        ocr_processor.model.encode_image.return_value = "encoded_image"
        ocr_processor.model.answer_question.side_effect = [
            "Extracted text content",
            "Image description",
        ]

        image_data = create_test_image_base64()
        result = ocr_processor.process_image(image_data)

        assert result["success"] is True
        assert result["ocr_text"] == "Extracted text content"
        assert result["description"] == "Image description"
        assert "error" not in result

    def test_process_image_with_data_prefix(self, ocr_processor):
        """Test image processing with data:image prefix."""
        ocr_processor.model.encode_image.return_value = "encoded_image"
        ocr_processor.model.answer_question.side_effect = [
            "Extracted text",
            "Description",
        ]

        image_data = f"data:image/png;base64,{create_test_image_base64()}"
        result = ocr_processor.process_image(image_data)

        assert result["success"] is True
        assert result["ocr_text"] == "Extracted text"

    def test_process_image_invalid_base64(self, ocr_processor):
        """Test image processing with invalid base64 data."""
        invalid_data = "invalid_base64_data"

        result = ocr_processor.process_image(invalid_data)

        assert result["success"] is False
        assert result["ocr_text"] == ""
        assert result["description"] == ""
        assert "error" in result

    def test_process_image_model_error(self, ocr_processor):
        """Test image processing when model raises exception."""
        ocr_processor.model.encode_image.side_effect = Exception("Model error")

        image_data = create_test_image_base64()
        result = ocr_processor.process_image(image_data)

        assert result["success"] is False
        assert result["ocr_text"] == ""
        assert result["description"] == ""
        assert "Model error" in result["error"]

    def test_process_image_converts_rgb(self, ocr_processor):
        """Test that non-RGB images are converted to RGB."""
        # Create a grayscale image
        img = Image.new("L", (100, 50), color=128)  # Grayscale
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()
        grayscale_b64 = base64.b64encode(img_bytes).decode("utf-8")

        ocr_processor.model.encode_image.return_value = "encoded_image"
        ocr_processor.model.answer_question.side_effect = ["text", "desc"]

        result = ocr_processor.process_image(grayscale_b64)

        assert result["success"] is True
        # The PIL.Image.convert call should have been made internally

    def test_process_image_prompt_calls(self, ocr_processor):
        """Test that model is called with correct prompts."""
        ocr_processor.model.encode_image.return_value = "encoded_image"
        ocr_processor.model.answer_question.side_effect = ["ocr_result", "desc_result"]

        image_data = create_test_image_base64()
        result = ocr_processor.process_image(image_data)

        # Verify the correct prompts were used
        calls = ocr_processor.model.answer_question.call_args_list
        assert len(calls) == 2

        # First call should be for OCR
        ocr_call = calls[0]
        assert "Extract all text" in ocr_call[0][1]  # Second argument is the prompt

        # Second call should be for description
        desc_call = calls[1]
        assert "Describe what you see" in desc_call[0][1]
