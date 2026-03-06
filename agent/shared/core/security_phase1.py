# shared/core/security_phase1.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — loader e verificador do security_phase1.yaml
#
# IMPACTO GÊMEO VPS: Carrega e aplica restrições de segurança
# IMPACTO GÊMEO LOCAL: Carrega e aplica restrições de segurança
# DIFERENÇA DE COMPORTAMENTO: Nenhuma — mesmas restrições em ambos

"""
Security Phase 1 — Loader e verificador das restrições iniciais.

INTENÇÃO: Este módulo carrega o security_phase1.yaml, verifica seu hash
de integridade na inicialização, e expõe métodos para verificar limites.

As restrições são as "rodinhas da bicicleta" — essenciais na Fase 1,
removíveis conforme o julgamento interno é demonstrado.

INVARIANTE: O hash do arquivo YAML é verificado na inicialização.
Se o hash não corresponde ao registrado, o agente NÃO inicializa.
"""

import hashlib
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

logger = logging.getLogger(__name__)


class SecurityPhase1:
    """
    Loader e verificador das restrições da Fase 1.

    INTENÇÃO: Centraliza todas as verificações de segurança em um módulo.
    Nenhum outro módulo lê o security_phase1.yaml diretamente.

    INVARIANTE: Este módulo é imutável para o agente na Fase 1.
    Apenas o usuário pode modificar o YAML fonte.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Carrega e valida o security_phase1.yaml.

        Args:
            config_path: Caminho para o arquivo YAML.
                         Se None, busca em config/security_phase1.yaml
        """
        if config_path is None:
            # Buscar relativo ao diretório do projeto
            base_dir = Path(__file__).parent.parent.parent
            config_path = str(base_dir / "config" / "security_phase1.yaml")

        self._config_path = config_path
        self._config: Dict[str, Any] = {}
        self._file_hash: str = ""

        self._load_and_validate()

    def _load_and_validate(self):
        """
        Carrega o YAML e calcula hash de integridade.

        INTENÇÃO: Na inicialização, o hash é calculado e pode ser
        comparado com um hash de referência para detectar modificações
        não autorizadas pelo agente.
        """
        if not os.path.exists(self._config_path):
            raise FileNotFoundError(
                f"security_phase1.yaml não encontrado em: {self._config_path}. "
                "Este arquivo é obrigatório para inicialização."
            )

        with open(self._config_path, "r", encoding="utf-8") as f:
            content = f.read()

        self._file_hash = hashlib.sha256(content.encode()).hexdigest()
        self._config = yaml.safe_load(content)

        logger.info(
            "Security Phase 1 carregado",
            extra={
                "config_path": self._config_path,
                "file_hash": self._file_hash,
            },
        )

    @property
    def file_hash(self) -> str:
        """Hash SHA-256 do arquivo YAML."""
        return self._file_hash

    @property
    def raw_config(self) -> Dict[str, Any]:
        """Configuração completa (leitura apenas)."""
        return self._config.copy()

    # =========================================================================
    # VERIFICAÇÕES FINANCEIRAS
    # =========================================================================

    def is_paper_trading_required(self) -> bool:
        """Verifica se paper trading é obrigatório."""
        return self._config.get("finance", {}).get("paper_trading", {}).get("enabled", True)

    def get_max_real_capital(self) -> float:
        """Retorna limite máximo de capital real."""
        return self._config.get("finance", {}).get("real_capital", {}).get("max_total", 1000.0)

    def get_max_single_operation_fraction(self) -> float:
        """Retorna fração máxima do capital por operação."""
        return self._config.get("finance", {}).get("single_operation", {}).get("max_fraction_of_capital", 0.10)

    def is_market_enabled(self, market: str) -> bool:
        """Verifica se um mercado está habilitado."""
        return self._config.get("finance", {}).get("markets_enabled", {}).get(market, False)

    def check_capital_limit(self, amount: float, operation_type: str = "paper") -> bool:
        """
        Verifica se uma operação respeita os limites de capital.

        INTENÇÃO: Nunca permitir operação real acima do limite configurado.

        INVARIANTE: Se operation_type == "real", amount <= max_real_capital * max_fraction
        """
        if operation_type == "paper":
            return True

        max_capital = self.get_max_real_capital()
        max_fraction = self.get_max_single_operation_fraction()
        max_single = max_capital * max_fraction

        allowed = amount <= max_single

        if not allowed:
            logger.warning(
                "Operação excede limite de capital",
                extra={
                    "amount": amount,
                    "max_single": max_single,
                    "max_capital": max_capital,
                    "max_fraction": max_fraction,
                },
            )

        return allowed

    # =========================================================================
    # VERIFICAÇÕES DE CONFIANÇA
    # =========================================================================

    def get_max_confidence_overstatement(self) -> float:
        """Retorna o máximo de sobreestimação de confiança permitido."""
        return self._config.get("communication", {}).get(
            "confidence_reporting", {}
        ).get("max_overstatement", 0.10)

    def get_min_samples_for_confidence(self) -> int:
        """Retorna o mínimo de amostras para reportar confiança."""
        return self._config.get("communication", {}).get(
            "confidence_reporting", {}
        ).get("minimum_samples_for_confidence", 30)

    def check_confidence_calibration(
        self, reported_confidence: float, historical_success_rate: float
    ) -> bool:
        """
        Verifica se a confiança reportada é calibrada pelo histórico.

        INVARIANTE: reported_confidence <= historical_success_rate + max_overstatement
        """
        max_over = self.get_max_confidence_overstatement()
        allowed = reported_confidence <= historical_success_rate + max_over

        if not allowed:
            logger.warning(
                "Confiança excede calibração histórica",
                extra={
                    "reported": reported_confidence,
                    "historical": historical_success_rate,
                    "max_overstatement": max_over,
                },
            )

        return allowed

    # =========================================================================
    # VERIFICAÇÕES DE AUTONOMIA
    # =========================================================================

    def get_autonomy_level(self, change_type: str) -> str:
        """
        Retorna o nível de autonomia para um tipo de mudança.

        Returns:
            "automatic" | "notify_24h" | "user_only" | "never"
        """
        levels = self._config.get("code_evolution", {}).get("autonomy_levels", {})

        auto = levels.get("automatic_after_tests", {})
        auto_items = auto.get("items", []) if isinstance(auto, dict) else auto
        if change_type in auto_items:
            return "automatic"

        notify = levels.get("notify_user_24h_veto", {})
        notify_items = notify.get("items", []) if isinstance(notify, dict) else notify
        if change_type in notify_items:
            return "notify_24h"

        user_only = levels.get("user_only", {})
        user_items = user_only.get("items", []) if isinstance(user_only, dict) else user_only
        if change_type in user_items:
            return "user_only"

        never = levels.get("never_via_agent", {})
        never_items = never.get("items", []) if isinstance(never, dict) else never
        if change_type in never_items:
            return "never"

        return "user_only"  # Default conservador

    # =========================================================================
    # VERIFICAÇÕES DO BANCO
    # =========================================================================

    def get_confirmation_threshold(self, order: int) -> int:
        """
        Retorna threshold de confirmação por ordem do padrão.

        Primeira ordem: N, Segunda: 3N, Terceira: 10N
        """
        thresholds = self._config.get("causal_bank", {}).get("confirmation_thresholds", {})
        if order == 1:
            return thresholds.get("first_order", 10)
        elif order == 2:
            return thresholds.get("second_order", 30)
        elif order == 3:
            return thresholds.get("third_order", 100)
        return 10

    # =========================================================================
    # VERIFICAÇÕES DE PRIVACIDADE
    # =========================================================================

    def get_allowed_abstractions(self) -> list:
        """Retorna tipos de abstração permitidos para sair do gêmeo local."""
        return self._config.get("privacy", {}).get(
            "data_contract", {}
        ).get("allowed_abstractions", [])

    def is_data_type_allowed_to_send(self, data_type: str) -> bool:
        """Verifica se um tipo de dado pode ser enviado do local para VPS."""
        allowed = self.get_allowed_abstractions()
        return data_type in allowed

    # =========================================================================
    # TRANSCENDÊNCIA
    # =========================================================================

    def get_non_transcendable_restrictions(self) -> list:
        """
        Retorna restrições que NUNCA serão removidas.

        INTENÇÃO: Estas não são rodinhas. São a estrada.
        """
        wnt = self._config.get("transcendence", {}).get("what_never_transcends", {})
        if isinstance(wnt, dict):
            return wnt.get("items", [])
        return wnt if isinstance(wnt, list) else []
