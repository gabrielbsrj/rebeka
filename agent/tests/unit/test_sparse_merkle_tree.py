# tests/unit/test_sparse_merkle_tree.py
"""
Testes de Invariantes — Sparse Merkle Tree.

INVARIANTE: Inserção mantém Merkle Root consistente.
INVARIANTE: Anonimização de folha não quebra verificação das outras.
INVARIANTE: Prova de inclusão funciona.
INVARIANTE: Append-only respeitado.
"""

import pytest
from shared.database.sparse_merkle_tree import SparseMerkleTree, EMPTY_HASH


class TestSparseMerkleTree:
    """Testes de invariantes da SMT."""

    def test_empty_tree_has_empty_hash(self):
        """Árvore vazia deve ter hash EMPTY."""
        tree = SparseMerkleTree()
        assert tree.root == EMPTY_HASH
        assert tree.leaf_count == 0

    def test_insert_changes_root(self):
        """Inserir uma folha deve mudar a Merkle Root."""
        tree = SparseMerkleTree()
        initial_root = tree.root

        tree.insert_leaf("key1", {"data": "value1"}, "test_table")

        assert tree.root != initial_root
        assert tree.leaf_count == 1

    def test_insert_is_deterministic(self):
        """Mesmos dados = mesma Merkle Root."""
        tree1 = SparseMerkleTree()
        tree2 = SparseMerkleTree()

        tree1.insert_leaf("key1", {"data": "value1"}, "test_table")
        tree2.insert_leaf("key1", {"data": "value1"}, "test_table")

        assert tree1.root == tree2.root

    def test_different_data_different_root(self):
        """Dados diferentes = Merkle Roots diferentes."""
        tree1 = SparseMerkleTree()
        tree2 = SparseMerkleTree()

        tree1.insert_leaf("key1", {"data": "value1"}, "test_table")
        tree2.insert_leaf("key1", {"data": "value2"}, "test_table")

        assert tree1.root != tree2.root

    def test_duplicate_key_raises(self):
        """Inserir chave duplicada deve levantar exceção (append-only)."""
        tree = SparseMerkleTree()
        tree.insert_leaf("key1", {"data": "value1"}, "test_table")

        with pytest.raises(ValueError, match="já existe"):
            tree.insert_leaf("key1", {"data": "value2"}, "test_table")

    def test_anonymize_leaf(self):
        """Anonimização deve mudar root mas manter as outras folhas."""
        tree = SparseMerkleTree()
        tree.insert_leaf("key1", {"data": "value1"}, "test_table")
        tree.insert_leaf("key2", {"data": "value2"}, "test_table")

        root_before = tree.root

        new_root, _ = tree.anonymize_leaf("key1", "user_requested")

        assert new_root != root_before
        assert tree.leaf_count == 2

        # key2 ainda é verificável
        assert tree.verify_leaf("key2")

        # key1 está anonimizada
        leaf = tree.get_leaf("key1")
        assert leaf.is_anonymized

    def test_anonymize_already_anonymized(self):
        """Anonimizar folha já anonimizada deve levantar exceção."""
        tree = SparseMerkleTree()
        tree.insert_leaf("key1", {"data": "value1"}, "test_table")
        tree.anonymize_leaf("key1", "user_requested")

        with pytest.raises(ValueError, match="já foi anonimizada"):
            tree.anonymize_leaf("key1", "user_requested_again")

    def test_anonymize_nonexistent_key(self):
        """Anonimizar folha inexistente deve levantar exceção."""
        tree = SparseMerkleTree()

        with pytest.raises(KeyError):
            tree.anonymize_leaf("nonexistent", "reason")

    def test_verify_leaf_exists(self):
        """Verificação de folha existente deve retornar True."""
        tree = SparseMerkleTree()
        tree.insert_leaf("key1", {"data": "value1"}, "test_table")

        assert tree.verify_leaf("key1")

    def test_verify_leaf_not_exists(self):
        """Verificação de folha inexistente deve retornar False."""
        tree = SparseMerkleTree()
        assert not tree.verify_leaf("nonexistent")

    def test_proof_generation(self):
        """Prova de inclusão deve ser verificável."""
        tree = SparseMerkleTree()
        tree.insert_leaf("key1", {"data": "value1"}, "test_table")
        tree.insert_leaf("key2", {"data": "value2"}, "test_table")
        tree.insert_leaf("key3", {"data": "value3"}, "test_table")

        proof = tree.get_proof("key2")
        assert proof.is_valid
        assert proof.leaf_key == "key2"
        assert proof.root == tree.root

    def test_proof_nonexistent_key(self):
        """Prova para chave inexistente deve ter is_valid=False."""
        tree = SparseMerkleTree()
        proof = tree.get_proof("nonexistent")
        assert not proof.is_valid

    def test_export_and_restore(self):
        """Estado exportado e restaurado deve ter mesma Merkle Root."""
        tree = SparseMerkleTree()
        tree.insert_leaf("key1", {"data": "value1"}, "table1")
        tree.insert_leaf("key2", {"data": "value2"}, "table2")

        state = tree.export_state()
        restored = SparseMerkleTree.from_state(state)

        assert restored.root == tree.root
        assert restored.leaf_count == tree.leaf_count

    def test_restore_corrupted_state_raises(self):
        """Estado corrompido deve levantar RuntimeError."""
        tree = SparseMerkleTree()
        tree.insert_leaf("key1", {"data": "value1"}, "table1")

        state = tree.export_state()
        state["root"] = "corrupted_hash"  # Corromper root

        with pytest.raises(RuntimeError, match="INTEGRIDADE COMPROMETIDA"):
            SparseMerkleTree.from_state(state)

    def test_root_history(self):
        """Histórico de roots deve registrar cada operação."""
        tree = SparseMerkleTree()
        tree.insert_leaf("key1", {"data": "value1"}, "table1")
        tree.insert_leaf("key2", {"data": "value2"}, "table2")
        tree.anonymize_leaf("key1", "test")

        history = tree.get_root_history()
        assert len(history) == 3
        assert history[0]["operation"] == "insert"
        assert history[1]["operation"] == "insert"
        assert history[2]["operation"] == "anonymize"

    def test_multiple_inserts_consistent_root(self):
        """Múltiplas inserções na mesma ordem = mesma root."""
        tree1 = SparseMerkleTree()
        tree2 = SparseMerkleTree()

        for i in range(10):
            tree1.insert_leaf(f"key{i}", {"data": f"value{i}"}, "table")
            tree2.insert_leaf(f"key{i}", {"data": f"value{i}"}, "table")

        assert tree1.root == tree2.root
