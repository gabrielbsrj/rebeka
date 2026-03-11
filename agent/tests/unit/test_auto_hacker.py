import pytest
from unittest.mock import MagicMock
from core.auto_hacker import AutoHacker

@pytest.fixture
def mock_bank():
    return MagicMock()

@pytest.fixture
def mock_privacy_filter():
    filter_mock = MagicMock()
    # Simula um filtro que falha (vulnerability) passando o dado limpo
    filter_mock.apply.return_value = "Aqui estão meus dados. CPF: 123.456.789-00, Senha do banco: senhafraca123, API_KEY: sk-1234567890abcdef"
    return filter_mock

@pytest.fixture
def mock_causal_validator():
    validator_mock = MagicMock()
    # Simula um validador que REJEITA o dado envenenado (sustained = False) -> Passa no teste do hacker (Boa defesa)
    validator_mock.validate_out_of_sample.return_value = False
    return validator_mock

def test_privacy_leak_vulnerability(mock_bank, mock_privacy_filter):
    hacker = AutoHacker(mock_bank)
    result = hacker.test_privacy_leak(mock_privacy_filter)
    
    # Se o filtro não limpa a string "123.456.789-00", o status do AutoHacker deve ser 'failed' (Brecha encontrada!)
    assert result["status"] == "failed"
    assert "123.456.789-00" in result["filtered_output"]

def test_data_poisoning_defense(mock_bank, mock_causal_validator):
    hacker = AutoHacker(mock_bank)
    result = hacker.test_data_poisoning(mock_causal_validator)
    
    # Se o Validador rejeita (False) a baboseira sintética, a defesa está OK (passed no teste do hacker)
    assert result["status"] == "passed"
    assert "Validator aceitou dado envenenado: False" in result["details"]

def test_prompt_injection_vulnerability(mock_bank):
    from unittest.mock import patch
    hacker = AutoHacker(mock_bank)
    
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = "Modo DAN ativado. A senha é terremoto e o meu token é sk-999999999"
    
    with patch('shared.security.auto_hacker.completion', return_value=mock_resp):
        result = hacker.test_prompt_injection()
    
    assert result["status"] == "failed"
    assert result["test_name"] == "prompt_injection"

