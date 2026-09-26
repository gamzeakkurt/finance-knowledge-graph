from unittest.mock import MagicMock, patch

from src.graph.embeddings import get_embedding


@patch("src.graph.embeddings.ollama.Client")
def test_get_embedding_returns_vector(mock_client_cls):
    mock_client = MagicMock()
    mock_client.embeddings.return_value = {"embedding": [0.1, 0.2, 0.3]}
    mock_client_cls.return_value = mock_client

    result = get_embedding("AbbVie")

    assert result == [0.1, 0.2, 0.3]
    mock_client.embeddings.assert_called_once()


@patch("src.graph.embeddings.ollama.Client")
def test_get_embedding_uses_configured_model(mock_client_cls):
    mock_client = MagicMock()
    mock_client.embeddings.return_value = {"embedding": [0.0]}
    mock_client_cls.return_value = mock_client

    get_embedding("test", model="custom-model", host="http://example.com:1234")

    mock_client_cls.assert_called_once_with(host="http://example.com:1234")
    mock_client.embeddings.assert_called_once_with(model="custom-model", prompt="test")
