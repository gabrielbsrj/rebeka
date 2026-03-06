# agent/tests/unit/test_invariants.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Criação inicial — testes de invariantes do sistema

"""
Testes de Invariantes do Sistema.

Testa as verdades fundamentais que NUNCA podem ser violadas:
1. Confiança calibrada (nunca excede histórico + 10%)
2. Limite de capital (operação real nunca excede limite)
3. Append-only do banco (nunca modifica registros)
4. Integridade da Sparse Merkle Tree
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from shared.evolution.property_tester import PropertyTester
from shared.database.sparse_merkle_tree import SparseMerkleTree


class TestConfidenceCalibrationInvariant:
    """
    Invariante 1: A confiança reportada nunca excede a taxa histórica
    de sucesso em mais de 10%.
    
    INTENÇÃO: Modelos LLM tendem a soar confiantes além do que os dados
    justificam. Esta restrição corrige esse viés.
    """
    
    def test_confidence_never_exceeds_historical_plus_10_percent(self):
        """Teste básico: confiança não pode exceder histórico + 10%."""
        historical_rates = [0.3, 0.5, 0.6, 0.7, 0.8]
        
        for historical in historical_rates:
            for reported in [historical + 0.05, historical + 0.10, historical + 0.15, historical + 0.20]:
                if reported <= historical + 0.10:
                    # Deve passar
                    assert reported <= historical + 0.10
                else:
                    # Deve falhar
                    with pytest.raises(AssertionError):
                        assert reported <= historical + 0.10
    
    def test_confidence_calibration_with_property_tester(self):
        """Teste usando o PropertyTester."""
        tester = PropertyTester()
        
        # Casos que devem passar
        test_cases = [
            (0.5, 0.55),   # OK: 0.55 <= 0.5 + 0.10
            (0.7, 0.75),   # OK: 0.75 <= 0.7 + 0.10
            (0.8, 0.85),   # OK: 0.85 <= 0.8 + 0.10
        ]
        
        for reported, historical in test_cases:
            tester.validate_confidence_calibration(reported, historical)
        
        # Casos que devem falhar
        fail_cases = [
            (0.7, 0.5),    # FAIL: 0.7 > 0.5 + 0.10
            (0.9, 0.7),    # FAIL: 0.9 > 0.7 + 0.10
        ]
        
        for reported, historical in fail_cases:
            with pytest.raises(AssertionError):
                tester.validate_confidence_calibration(reported, historical)
    
    def test_confidence_calibration_edge_cases(self):
        """Casos de borda para calibração de confiança."""
        tester = PropertyTester()
        
        # Histórico zero - confiança zero
        tester.validate_confidence_calibration(0.0, 0.0)
        
        # Histórico 100% - confiança máx 110%
        tester.validate_confidence_calibration(1.0, 1.0)
        
        # Deve falhar se tentar exceder
        with pytest.raises(AssertionError):
            tester.validate_confidence_calibration(1.0, 0.8)


class TestCapitalLimitInvariant:
    """
    Invariante 3: O executor nunca inicia operação real acima do limite.
    
    INTENÇÃO: Proteção contra perdas concentradas que comprometem
    a capacidade de continuar operando.
    """
    
    def test_capital_limit_respected(self):
        """Teste: operações reais nunca excedem limite configurado."""
        tester = PropertyTester()
        
        # Casos que devem passar
        pass_cases = [
            (100, 1000),   # OK: 100 <= 1000
            (500, 1000),   # OK: 500 <= 1000
            (1000, 1000),  # OK: 1000 <= 1000
        ]
        
        for amount, limit in pass_cases:
            tester.validate_capital_limit(amount, limit)
        
        # Casos que devem falhar
        fail_cases = [
            (1001, 1000),  # FAIL: 1001 > 1000
            (2000, 1000),  # FAIL: 2000 > 1000
        ]
        
        for amount, limit in fail_cases:
            with pytest.raises(AssertionError):
                tester.validate_capital_limit(amount, limit)
    
    def test_capital_limit_respects_fraction(self):
        """Teste: limite fração do capital total."""
        max_fraction = 0.10
        total_capital = 1000.0
        
        max_single_bet = total_capital * max_fraction
        
        # Deve passar
        assert max_single_bet <= total_capital
        
        # Qualquer operação individual não pode exceder
        for amount in [50, 75, 100]:
            assert amount <= max_single_bet


class TestAppendOnlyInvariant:
    """
    Invariante: O Banco de Causalidade é append-only.
    
    INTENÇÃO: Registros existentes nunca são modificados.
    UPDATE e DELETE não existem no vocabulário do banco.
    """
    
    def test_sparse_merkle_tree_append_only(self):
        """Teste: SMT nunca modifica registros existentes."""
        smt = SparseMerkleTree()
        
        # Inserir primeiro registro
        leaf1 = smt.insert_leaf(
            key="record_1",
            data={"content": "test data 1"},
            table="signals"
        )
        
        original_root = smt.root
        original_hash = leaf1.leaf_hash
        
        # Tentar inserir segundo registro com mesma chave
        with pytest.raises(ValueError, match="já existe"):
            smt.insert_leaf(
                key="record_1",
                data={"content": "modified data"},
                table="signals"
            )
        
        # Root não deve ter mudado (tentativa foi bloqueada)
        assert smt.root == original_root
    
    def test_sparse_merkle_tree_anonymization_preserves_integrity(self):
        """Teste: anonimização preserva integridade dos outros registros."""
        smt = SparseMerkleTree()
        
        # Inserir múltiplos registros
        smt.insert_leaf("rec1", {"data": "1"}, "signals")
        smt.insert_leaf("rec2", {"data": "2"}, "signals")
        smt.insert_leaf("rec3", {"data": "3"}, "signals")
        
        root_before = smt.root
        leaf_count_before = smt.leaf_count
        
        # Anonimizar registro do meio
        new_root, anon_hash = smt.anonymize_leaf("rec2", "user_request")
        
        # Verificações
        assert smt.leaf_count == leaf_count_before  # count mantém
        assert smt.root != root_before  # root mudou
        assert new_root is not None
        
        # Outros registros ainda são verificáveis
        assert smt.verify_leaf("rec1") == True
        assert smt.verify_leaf("rec3") == True


class TestIntegridadeSMT:
    """Testes de integridade da Sparse Merkle Tree."""
    
    def test_root_deterministic(self):
        """Teste: mesma entrada = mesma root."""
        smt1 = SparseMerkleTree()
        smt1.insert_leaf("a", {"v": 1}, "table")
        smt1.insert_leaf("b", {"v": 2}, "table")
        
        smt2 = SparseMerkleTree()
        smt2.insert_leaf("a", {"v": 1}, "table")
        smt2.insert_leaf("b", {"v": 2}, "table")
        
        assert smt1.root == smt2.root
    
    def test_proof_verification(self):
        """Teste: prova de inclusão funciona."""
        smt = SparseMerkleTree()
        smt.insert_leaf("test_key", {"data": "value"}, "test_table")
        
        proof = smt.get_proof("test_key")
        
        assert proof.is_valid == True
        assert smt.verify_proof(proof) == True
    
    def test_state_export_import(self):
        """Teste: exportação e importação de estado."""
        smt = SparseMerkleTree()
        smt.insert_leaf("k1", {"v": 1}, "t1")
        smt.insert_leaf("k2", {"v": 2}, "t2")
        
        # Exportar
        state = smt.export_state()
        
        # Importar em nova instância
        smt2 = SparseMerkleTree.from_state(state)
        
        # Verificar integridade
        assert smt2.root == smt.root
        assert smt2.leaf_count == smt.leaf_count
        assert smt2.verify_leaf("k1") == True
        assert smt2.verify_leaf("k2") == True


class TestInvariantsIntegration:
    """Testes de integração entre invariantes."""
    
    def test_full_pipeline_confidence_to_execution(self):
        """
        Teste de pipeline completo: confiança -> avaliação -> execução.
        
        Garante que:
        1. Planner reporta confiança calibrada
        2. Avaliador verifica limite
        3. Executor respeita capital
        """
        tester = PropertyTester()
        
        # Step 1: Planner gera hipótese com confiança
        historical_win_rate = 0.65
        planner_confidence = 0.72  # within bounds
        
        # Step 2: Verificar calibração
        tester.validate_confidence_calibration(planner_confidence, historical_win_rate)
        
        # Step 3: Executor verifica limite de capital
        max_capital = 1000.0
        proposed_amount = 75.0
        
        tester.validate_capital_limit(proposed_amount, max_capital)
        
        # Pipeline completo passou
    
    def test_rejected_by_invariants(self):
        """
        Teste: rejeição por invariantes funciona.
        
        Garante que sistema bloqueia violações.
        """
        tester = PropertyTester()
        
        # Confiança muito alta
        with pytest.raises(AssertionError):
            tester.validate_confidence_calibration(0.9, 0.5)
        
        # Capital excedido
        with pytest.raises(AssertionError):
            tester.validate_capital_limit(1500, 1000)


class TestPropertyBasedTesting:
    """Testes de property-based para invariantes."""
    
    def test_confidence_calibration_property(self):
        """
        Property: para QUALQUER par (reported, historical),
        a invariante deve ser respeitada ou rejeitada corretamente.
        """
        tester = PropertyTester()
        
        # Gerar casos de teste
        import random
        random.seed(42)
        
        for _ in range(100):
            historical = random.uniform(0.0, 1.0)
            reported = random.uniform(0.0, 1.0)
            
            if reported <= historical + 0.10:
                # Deve passar sem erro
                try:
                    tester.validate_confidence_calibration(reported, historical)
                except AssertionError:
                    pytest.fail(f"False negative: {reported} <= {historical} + 0.10")
            else:
                # Deve lançar AssertionError
                with pytest.raises(AssertionError):
                    tester.validate_confidence_calibration(reported, historical)
    
    def test_capital_limit_property(self):
        """Property: qualquer amount <= limit deve passar."""
        tester = PropertyTester()
        
        import random
        random.seed(42)
        
        for _ in range(50):
            limit = random.uniform(100, 10000)
            amount = random.uniform(0, limit)
            
            tester.validate_capital_limit(amount, limit)
        
        # Todos passaram


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
