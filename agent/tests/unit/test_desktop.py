# agent/tests/unit/test_desktop.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Criação inicial — testes para DesktopController

"""
Testes unitários para DesktopController.

INTENÇÃO: Garantir que a automação de desktop funciona corretamente
com mock do PyAutoGUI para evitar ações reais durante testes.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os


@pytest.fixture
def mock_pyautogui():
    """Fixture para mockar pyautogui em todos os testes."""
    with patch.dict("sys.modules", {"pyautogui": MagicMock()}):
        yield


class TestDesktopControllerInit:
    """Testes de inicialização."""

    def test_init_default(self, mock_pyautogui):
        """Deve inicializar com valores padrão."""
        from local.desktop import DesktopController
        
        controller = DesktopController()
        assert controller._vault is None
        assert controller._safety_timeout == 2.0
        assert controller._action_log == []

    def test_init_with_vault(self, mock_pyautogui):
        """Deve aceitar vault opcional."""
        from local.desktop import DesktopController
        
        mock_vault = Mock()
        controller = DesktopController(vault=mock_vault)
        assert controller._vault is mock_vault


class TestVaultResolution:
    """Testes para resolução de vault pointers."""

    def test_resolve_no_vault(self, mock_pyautogui):
        """Sem vault, texto permanece inalterado."""
        from local.desktop import DesktopController
        
        controller = DesktopController()
        result = controller._resolve_vault_pointers("senha123")
        assert result == "senha123"

    def test_resolve_no_pointer(self, mock_pyautogui):
        """Texto sem pointer permanece inalterado."""
        from local.desktop import DesktopController
        
        mock_vault = Mock()
        controller = DesktopController(vault=mock_vault)
        result = controller._resolve_vault_pointers("texto normal")
        assert result == "texto normal"

    def test_resolve_with_pointer(self, mock_pyautogui):
        """Deve resolver vault:// pointer."""
        from local.desktop import DesktopController
        
        mock_vault = Mock()
        mock_vault.get_secret.return_value = {"value": "minha_senha_secreta"}
        
        controller = DesktopController(vault=mock_vault)
        result = controller._resolve_vault_pointers("vault://senha_email")
        assert result == "minha_senha_secreta"

    def test_resolve_multiple_pointers(self, mock_pyautogui):
        """Deve resolver múltiplos pointers."""
        from local.desktop import DesktopController
        
        mock_vault = Mock()
        mock_vault.get_secret.side_effect = lambda k: {"value": f"val_{k}"}
        
        controller = DesktopController(vault=mock_vault)
        result = controller._resolve_vault_pointers("user: vault://user, pass: vault://pass")
        assert "val_user" in result
        assert "val_pass" in result


class TestMouseOperations:
    """Testes para operações de mouse."""

    def test_move_mouse(self, mock_pyautogui):
        """Deve mover mouse para posição."""
        from local.desktop import DesktopController
        import pyautogui
        
        controller = DesktopController()
        result = controller.move_mouse(100, 200)
        
        pyautogui.moveTo.assert_called_once()
        assert result["status"] == "success"
        assert result["x"] == 100
        assert result["y"] == 200

    def test_click_coordinates(self, mock_pyautogui):
        """Deve clicar em coordenadas."""
        from local.desktop import DesktopController
        import pyautogui
        
        controller = DesktopController()
        result = controller.click(100, 200)
        
        pyautogui.click.assert_called_once()
        assert result["status"] == "success"
        assert result["method"] == "coordinates"

    def test_click_image_found(self, mock_pyautogui):
        """Deve clicar em imagem encontrada."""
        from local.desktop import DesktopController
        import pyautogui
        
        pyautogui.locateOnScreen.return_value = MagicMock(
            left=100, top=100, width=50, height=50
        )
        pyautogui.center.return_value = MagicMock(x=125, y=125)
        
        controller = DesktopController()
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image")
            temp_path = f.name
        
        try:
            result = controller.click(image=temp_path)
            assert result["status"] == "success"
            assert result["method"] == "image"
        finally:
            os.unlink(temp_path)

    def test_click_image_not_found(self, mock_pyautogui):
        """Deve retornar erro se imagem não encontrada."""
        from local.desktop import DesktopController
        import pyautogui
        
        pyautogui.locateOnScreen.return_value = None
        
        controller = DesktopController()
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image")
            temp_path = f.name
        
        try:
            result = controller.click(image=temp_path)
            assert result["status"] == "error"
        finally:
            os.unlink(temp_path)

    def test_double_click(self, mock_pyautogui):
        """Deve fazer clique duplo."""
        from local.desktop import DesktopController
        import pyautogui
        
        controller = DesktopController()
        result = controller.double_click(100, 200)
        
        pyautogui.click.assert_called_once()
        call_kwargs = pyautogui.click.call_args[1]
        assert call_kwargs["clicks"] == 2

    def test_right_click(self, mock_pyautogui):
        """Deve fazer clique direito."""
        from local.desktop import DesktopController
        import pyautogui
        
        controller = DesktopController()
        result = controller.right_click(100, 200)
        
        pyautogui.click.assert_called_once()
        call_kwargs = pyautogui.click.call_args[1]
        assert call_kwargs["button"] == "right"

    def test_scroll(self, mock_pyautogui):
        """Deve rolar a tela."""
        from local.desktop import DesktopController
        import pyautogui
        
        controller = DesktopController()
        result = controller.scroll(5)
        
        pyautogui.scroll.assert_called_once()
        assert result["status"] == "success"


class TestKeyboardOperations:
    """Testes para operações de teclado."""

    def test_type_text_basic(self, mock_pyautogui):
        """Deve digitar texto."""
        from local.desktop import DesktopController
        import pyautogui
        
        controller = DesktopController()
        result = controller.type_text("hello world")
        
        pyautogui.write.assert_called_once_with("hello world", interval=0.05)
        assert result["status"] == "success"

    def test_type_text_with_vault(self, mock_pyautogui):
        """Deve resolver vault pointer ao digitar."""
        from local.desktop import DesktopController
        import pyautogui
        
        mock_vault = Mock()
        mock_vault.get_secret.return_value = {"password": "secret123"}
        
        controller = DesktopController(vault=mock_vault)
        result = controller.type_text("vault://senha")
        
        pyautogui.write.assert_called_once_with("secret123", interval=0.05)
        assert result["status"] == "success"

    def test_press_keys(self, mock_pyautogui):
        """Deve pressionar teclas."""
        from local.desktop import DesktopController
        import pyautogui
        
        controller = DesktopController()
        result = controller.press("enter", "tab")
        
        assert pyautogui.press.call_count == 2
        assert result["status"] == "success"

    def test_hotkey(self, mock_pyautogui):
        """Deve executar atalho."""
        from local.desktop import DesktopController
        import pyautogui
        
        controller = DesktopController()
        result = controller.hotkey("ctrl", "c")
        
        pyautogui.hotkey.assert_called_once_with("ctrl", "c")
        assert result["status"] == "success"


class TestScreenshot:
    """Testes para screenshot."""

    def test_screenshot_default_path(self, mock_pyautogui):
        """Deve capturar screenshot em temp."""
        from local.desktop import DesktopController
        import pyautogui
        
        mock_screenshot = Mock()
        mock_screenshot.save = Mock()
        pyautogui.screenshot.return_value = mock_screenshot
        
        controller = DesktopController()
        result = controller.screenshot()
        
        assert result["status"] == "success"
        assert "path" in result
        assert len(controller._temp_screenshots) == 1

    def test_screenshot_custom_path(self, mock_pyautogui):
        """Deve salvar em caminho customizado."""
        from local.desktop import DesktopController
        import pyautogui
        
        mock_screenshot = Mock()
        mock_screenshot.save = Mock()
        pyautogui.screenshot.return_value = mock_screenshot
        
        controller = DesktopController()
        result = controller.screenshot(save_path="/tmp/test.png")
        
        assert result["status"] == "success"
        assert result["path"] == "/tmp/test.png"

    def test_screenshot_with_region(self, mock_pyautogui):
        """Deve capturar região específica."""
        from local.desktop import DesktopController
        import pyautogui
        
        mock_screenshot = Mock()
        mock_screenshot.save = Mock()
        pyautogui.screenshot.return_value = mock_screenshot
        
        controller = DesktopController()
        result = controller.screenshot(region=(0, 0, 100, 100))
        
        pyautogui.screenshot.assert_called_once_with(region=(0, 0, 100, 100))
        assert result["status"] == "success"


class TestFindImage:
    """Testes para busca de imagem."""

    def test_find_image_found(self, mock_pyautogui):
        """Deve encontrar imagem na tela."""
        from local.desktop import DesktopController
        import pyautogui
        
        pyautogui.locateOnScreen.return_value = MagicMock(
            left=100, top=100, width=50, height=50
        )
        pyautogui.center.return_value = MagicMock(x=125, y=125)
        
        controller = DesktopController()
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake")
            temp_path = f.name
        
        try:
            result = controller.find_image(temp_path)
            assert result["status"] == "success"
            assert result["found"] is True
            assert "location" in result
        finally:
            os.unlink(temp_path)

    def test_find_image_not_found(self, mock_pyautogui):
        """Deve retornar found=False se não encontrar."""
        from local.desktop import DesktopController
        import pyautogui
        
        pyautogui.locateOnScreen.return_value = None
        
        controller = DesktopController()
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake")
            temp_path = f.name
        
        try:
            result = controller.find_image(temp_path)
            assert result["status"] == "success"
            assert result["found"] is False
        finally:
            os.unlink(temp_path)

    def test_find_image_file_not_exists(self, mock_pyautogui):
        """Deve retornar erro se arquivo não existe."""
        from local.desktop import DesktopController
        
        controller = DesktopController()
        result = controller.find_image("/nonexistent/image.png")
        
        assert result["status"] == "error"


class TestWindowOperations:
    """Testes para operações de janela."""

    def test_get_mouse_position(self, mock_pyautogui):
        """Deve retornar posição do mouse."""
        from local.desktop import DesktopController
        import pyautogui
        
        pyautogui.position.return_value = (100, 200)
        
        controller = DesktopController()
        result = controller.get_mouse_position()
        
        assert result["status"] == "success"
        assert result["x"] == 100
        assert result["y"] == 200

    def test_get_screen_size(self, mock_pyautogui):
        """Deve retornar tamanho da tela."""
        from local.desktop import DesktopController
        import pyautogui
        
        pyautogui.size.return_value = (1920, 1080)
        
        controller = DesktopController()
        result = controller.get_screen_size()
        
        assert result["status"] == "success"
        assert result["width"] == 1920
        assert result["height"] == 1080

    def test_get_active_window(self, mock_pyautogui):
        """Deve retornar info da janela ativa."""
        from local.desktop import DesktopController
        
        mock_window = Mock()
        mock_window.title = "Test Window"
        mock_window.left = 0
        mock_window.top = 0
        mock_window.width = 800
        mock_window.height = 600
        
        with patch.dict("sys.modules", {"pygetwindow": MagicMock(getActiveWindow=Mock(return_value=mock_window))}):
            controller = DesktopController()
            result = controller.get_active_window()
            
            assert result["status"] == "success"
            assert result["title"] == "Test Window"


class TestDialogs:
    """Testes para diálogos."""

    def test_alert(self, mock_pyautogui):
        """Deve mostrar alerta."""
        from local.desktop import DesktopController
        import pyautogui
        
        controller = DesktopController()
        result = controller.alert("Test message")
        
        pyautogui.alert.assert_called_once()
        assert result["status"] == "success"

    def test_confirm_ok(self, mock_pyautogui):
        """Deve mostrar confirmação e retornar True."""
        from local.desktop import DesktopController
        import pyautogui
        
        pyautogui.confirm.return_value = "OK"
        
        controller = DesktopController()
        result = controller.confirm("Continue?")
        
        assert result["status"] == "success"
        assert result["confirmed"] is True

    def test_confirm_cancel(self, mock_pyautogui):
        """Deve mostrar confirmação e retornar False."""
        from local.desktop import DesktopController
        import pyautogui
        
        pyautogui.confirm.return_value = "Cancel"
        
        controller = DesktopController()
        result = controller.confirm("Continue?")
        
        assert result["status"] == "success"
        assert result["confirmed"] is False

    def test_prompt(self, mock_pyautogui):
        """Deve mostrar prompt de entrada."""
        from local.desktop import DesktopController
        import pyautogui
        
        pyautogui.prompt.return_value = "user input"
        
        controller = DesktopController()
        result = controller.prompt("Enter value:")
        
        assert result["status"] == "success"
        assert result["value"] == "user input"
        assert result["cancelled"] is False

    def test_prompt_cancelled(self, mock_pyautogui):
        """Deve detectar prompt cancelado."""
        from local.desktop import DesktopController
        import pyautogui
        
        pyautogui.prompt.return_value = None
        
        controller = DesktopController()
        result = controller.prompt("Enter value:")
        
        assert result["status"] == "success"
        assert result["cancelled"] is True


class TestCleanup:
    """Testes para limpeza."""

    def test_cleanup_removes_temp_screenshots(self, mock_pyautogui):
        """Deve remover screenshots temporários."""
        from local.desktop import DesktopController
        
        controller = DesktopController()
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake")
            temp_path = f.name
        
        controller._temp_screenshots.append(temp_path)
        
        assert os.path.exists(temp_path)
        controller.cleanup()
        
        assert not os.path.exists(temp_path)
        assert len(controller._temp_screenshots) == 0


class TestActionLog:
    """Testes para log de ações."""

    def test_action_log_records(self, mock_pyautogui):
        """Deve registrar ações no log."""
        from local.desktop import DesktopController
        
        controller = DesktopController()
        controller.click(100, 200)
        
        log = controller.get_action_log()
        assert len(log) == 1
        assert log[0]["action"] == "click"

    def test_action_log_limit(self, mock_pyautogui):
        """Deve limitar log retornado."""
        from local.desktop import DesktopController
        
        controller = DesktopController()
        
        for i in range(200):
            controller.click(i, i)
        
        log = controller.get_action_log(limit=10)
        assert len(log) == 10

    def test_clear_action_log(self, mock_pyautogui):
        """Deve limpar log de ações."""
        from local.desktop import DesktopController
        
        controller = DesktopController()
        controller.click(100, 200)
        
        controller.clear_action_log()
        
        assert len(controller._action_log) == 0
