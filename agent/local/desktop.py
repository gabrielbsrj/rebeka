# agent/local/desktop.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Criação inicial — automação de desktop via PyAutoGUI
#
# IMPACTO GÊMEO VPS: Nenhum — módulo exclusivo do gêmeo local
# IMPACTO GÊMEO LOCAL: Automação motor completa do desktop
# DIFERENÇA DE COMPORTAMENTO: N/A — só existe no local

"""
Desktop Controller — Controle motor do desktop via PyAutoGUI.

INTENÇÃO: Fornece automação de desktop completa: mouse, teclado, captura
de tela, busca de imagens e gerenciamento de janelas. Toda operação é
reversível e logged para auditabilidade.

INVARIANTE: Nenhuma credencial é digitada diretamente — usa vault:// pointers.
INVARIANTE: Toda ação destrutiva requer confirmação ou mandato explícito.
INVARIANTE: Screenshots temporários são limpos após uso.
"""

import logging
import os
import time
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from local.vault.master_vault import MasterVault

logger = logging.getLogger(__name__)


class DesktopController:
    """
    Controlador de desktop via PyAutoGUI.
    
    INTENÇÃO: Automatiza interações com o desktop de forma segura
    e auditável. Integrado ao Master Vault para injeção cega de credenciais.
    """

    def __init__(self, vault: Optional["MasterVault"] = None, safety_timeout: float = 2.0):
        self._vault = vault
        self._safety_timeout = safety_timeout
        self._action_log: List[Dict[str, Any]] = []
        self._temp_screenshots: List[str] = []
        
        self._configure_pyautogui()
    
    def _configure_pyautogui(self):
        """Configura PyAutoGUI com defaults seguros."""
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
    
    def _log_action(self, action: str, details: Dict[str, Any]) -> None:
        """Registra ação para auditabilidade."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
        }
        self._action_log.append(entry)
        logger.debug(f"Desktop action: {action} - {details}")
    
    def _resolve_vault_pointers(self, text: str) -> str:
        """
        Resolve vault:// pointers no último milissegundo.
        
        INTENÇÃO: Credenciais nunca aparecem em logs ou contextos de LLM.
        """
        if not self._vault or "vault://" not in text:
            return text
        
        import re
        pointers = re.findall(r"vault://([\w-]+)", text)
        resolved = text
        
        for pointer in pointers:
            secret = self._vault.get_secret(pointer)
            if secret:
                val = secret.get("value") or secret.get("password") or str(secret)
                resolved = resolved.replace(f"vault://{pointer}", val)
            else:
                logger.warning(f"Vault pointer não resolvido: {pointer}")
        
        return resolved
    
    def move_mouse(self, x: int, y: int, duration: float = 0.5) -> Dict[str, Any]:
        """Move o mouse para posição absoluta."""
        import pyautogui
        try:
            pyautogui.moveTo(x, y, duration=duration)
            self._log_action("move_mouse", {"x": x, "y": y})
            return {"status": "success", "x": x, "y": y}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def click(
        self, 
        x: Optional[int] = None, 
        y: Optional[int] = None, 
        button: str = "left",
        clicks: int = 1,
        image: Optional[str] = None,
        confidence: float = 0.9
    ) -> Dict[str, Any]:
        """
        Executa clique na posição ou imagem.
        
        Args:
            x, y: Coordenadas absolutas (se image=None)
            button: "left", "right", "middle"
            clicks: Número de cliques (2 para duplo)
            image: Caminho para imagem a localizar
            confidence: Confiança mínima para matching de imagem
        """
        import pyautogui
        
        try:
            if image and os.path.exists(image):
                location = pyautogui.locateOnScreen(image, confidence=confidence)
                if location:
                    center = pyautogui.center(location)
                    pyautogui.click(center.x, center.y, button=button, clicks=clicks)
                    self._log_action("click_image", {"image": image, "button": button})
                    return {"status": "success", "method": "image", "location": (center.x, center.y)}
                else:
                    return {"status": "error", "message": f"Imagem não encontrada: {image}"}
            
            elif x is not None and y is not None:
                pyautogui.click(x, y, button=button, clicks=clicks)
                self._log_action("click", {"x": x, "y": y, "button": button})
                return {"status": "success", "method": "coordinates", "location": (x, y)}
            
            else:
                pyautogui.click(button=button, clicks=clicks)
                self._log_action("click_current", {"button": button})
                return {"status": "success", "method": "current_position"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None, image: Optional[str] = None) -> Dict[str, Any]:
        """Atalho para clique duplo."""
        return self.click(x, y, clicks=2, image=image)
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None, image: Optional[str] = None) -> Dict[str, Any]:
        """Atalho para clique direito."""
        return self.click(x, y, button="right", image=image)
    
    def drag(
        self, 
        start_x: int, 
        start_y: int, 
        end_x: int, 
        end_y: int,
        duration: float = 1.0,
        button: str = "left"
    ) -> Dict[str, Any]:
        """Arrasta de (start_x, start_y) até (end_x, end_y)."""
        import pyautogui
        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)
            self._log_action("drag", {"from": (start_x, start_y), "to": (end_x, end_y)})
            return {"status": "success", "from": (start_x, start_y), "to": (end_x, end_y)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        """
        Rola a tela.
        
        Args:
            clicks: Positivo para cima, negativo para baixo
        """
        import pyautogui
        try:
            if x is not None and y is not None:
                pyautogui.scroll(clicks, x, y)
            else:
                pyautogui.scroll(clicks)
            self._log_action("scroll", {"clicks": clicks})
            return {"status": "success", "clicks": clicks}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def type_text(
        self, 
        text: str, 
        interval: float = 0.05,
        resolve_vault: bool = True
    ) -> Dict[str, Any]:
        """
        Digita texto no foco atual.
        
        Args:
            text: Texto a digitar (pode conter vault:// pointers)
            interval: Intervalo entre teclas
            resolve_vault: Se True, resolve vault:// pointers
        """
        import pyautogui
        try:
            final_text = self._resolve_vault_pointers(text) if resolve_vault else text
            pyautogui.write(final_text, interval=interval)
            
            safe_text = "[VAULT_INJECTED]" if resolve_vault and "vault://" in text else text
            self._log_action("type_text", {"text_length": len(text), "preview": safe_text[:50]})
            
            return {"status": "success", "length": len(final_text)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def press(self, *keys: str) -> Dict[str, Any]:
        """Pressiona teclas individuais."""
        import pyautogui
        try:
            for key in keys:
                pyautogui.press(key)
            self._log_action("press", {"keys": list(keys)})
            return {"status": "success", "keys": list(keys)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def hotkey(self, *keys: str) -> Dict[str, Any]:
        """Executa atalho de teclado (ex: hotkey('ctrl', 'c'))."""
        import pyautogui
        try:
            pyautogui.hotkey(*keys)
            self._log_action("hotkey", {"keys": list(keys)})
            return {"status": "success", "keys": list(keys)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def screenshot(
        self, 
        region: Optional[Tuple[int, int, int, int]] = None,
        save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Captura screenshot.
        
        Args:
            region: (left, top, width, height) ou None para tela inteira
            save_path: Caminho para salvar. Se None, usa temp.
        
        Returns:
            Dict com status e caminho do arquivo
        """
        import pyautogui
        try:
            if save_path is None:
                fd, save_path = tempfile.mkstemp(suffix=".png", prefix="rebeka_screenshot_")
                os.close(fd)
                self._temp_screenshots.append(save_path)
            
            screenshot = pyautogui.screenshot(region=region)
            screenshot.save(save_path)
            
            self._log_action("screenshot", {"path": save_path, "region": region})
            return {"status": "success", "path": save_path, "region": region}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def find_image(
        self, 
        image_path: str, 
        confidence: float = 0.9,
        grayscale: bool = False
    ) -> Dict[str, Any]:
        """
        Localiza uma imagem na tela.
        
        Returns:
            Dict com 'found' (bool), 'location' (x, y) se encontrado
        """
        import pyautogui
        try:
            if not os.path.exists(image_path):
                return {"status": "error", "message": f"Arquivo não existe: {image_path}"}
            
            location = pyautogui.locateOnScreen(
                image_path, 
                confidence=confidence,
                grayscale=grayscale
            )
            
            if location:
                center = pyautogui.center(location)
                return {
                    "status": "success",
                    "found": True,
                    "location": (center.x, center.y),
                    "box": (location.left, location.top, location.width, location.height)
                }
            else:
                return {"status": "success", "found": False}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def wait_for_image(
        self, 
        image_path: str, 
        timeout: float = 30.0,
        confidence: float = 0.9,
        check_interval: float = 0.5
    ) -> Dict[str, Any]:
        """Aguarda até que uma imagem apareça na tela."""
        import pyautogui
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.find_image(image_path, confidence)
            if result.get("found"):
                return result
            time.sleep(check_interval)
        
        return {"status": "timeout", "message": f"Imagem não apareceu em {timeout}s"}
    
    def get_mouse_position(self) -> Dict[str, Any]:
        """Retorna posição atual do mouse."""
        import pyautogui
        x, y = pyautogui.position()
        return {"status": "success", "x": x, "y": y}
    
    def get_screen_size(self) -> Dict[str, Any]:
        """Retorna dimensões da tela."""
        import pyautogui
        width, height = pyautogui.size()
        return {"status": "success", "width": width, "height": height}
    
    def get_active_window(self) -> Dict[str, Any]:
        """Retorna informações da janela ativa."""
        try:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window:
                return {
                    "status": "success",
                    "title": window.title,
                    "left": window.left,
                    "top": window.top,
                    "width": window.width,
                    "height": window.height,
                }
            return {"status": "success", "title": None}
        except ImportError:
            return {"status": "error", "message": "pygetwindow não instalado"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def activate_window(self, title_pattern: str) -> Dict[str, Any]:
        """Ativa janela pelo título (pattern matching)."""
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title_pattern)
            if windows:
                windows[0].activate()
                self._log_action("activate_window", {"title": windows[0].title})
                return {"status": "success", "title": windows[0].title}
            return {"status": "error", "message": f"Janela não encontrada: {title_pattern}"}
        except ImportError:
            return {"status": "error", "message": "pygetwindow não instalado"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def close_window(self, title_pattern: str) -> Dict[str, Any]:
        """Fecha janela pelo título."""
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title_pattern)
            if windows:
                windows[0].close()
                self._log_action("close_window", {"title": windows[0].title})
                return {"status": "success", "title": windows[0].title}
            return {"status": "error", "message": f"Janela não encontrada: {title_pattern}"}
        except ImportError:
            return {"status": "error", "message": "pygetwindow não instalado"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def alert(self, message: str, title: str = "Rebeka", timeout: Optional[float] = None) -> Dict[str, Any]:
        """Mostra alerta na tela."""
        import pyautogui
        try:
            pyautogui.alert(text=message, title=title, timeout=timeout)
            self._log_action("alert", {"message": message[:100]})
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def confirm(
        self, 
        message: str, 
        title: str = "Rebeka - Confirmação",
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Mostra diálogo de confirmação."""
        import pyautogui
        try:
            result = pyautogui.confirm(text=message, title=title, timeout=timeout)
            self._log_action("confirm", {"message": message[:100], "result": result})
            return {"status": "success", "confirmed": result == "OK", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def prompt(
        self,
        message: str,
        title: str = "Rebeka",
        default: str = "",
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Mostra prompt de entrada de texto."""
        import pyautogui
        try:
            result = pyautogui.prompt(text=message, title=title, default=default, timeout=timeout)
            self._log_action("prompt", {"message": message[:100]})
            return {"status": "success", "value": result, "cancelled": result is None}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def cleanup(self) -> None:
        """Remove screenshots temporários."""
        for path in self._temp_screenshots:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.warning(f"Falha ao remover temp screenshot {path}: {e}")
        self._temp_screenshots.clear()
        logger.info("Screenshots temporários limpos")
    
    def get_action_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna log de ações recentes."""
        return self._action_log[-limit:]
    
    def clear_action_log(self) -> None:
        """Limpa o log de ações."""
        self._action_log.clear()
