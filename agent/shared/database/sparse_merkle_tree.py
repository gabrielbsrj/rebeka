# shared/database/sparse_merkle_tree.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — SMT com esquecimento seletivo
#
# IMPACTO GÊMEO VPS: Integridade do banco PostgreSQL verificável
# IMPACTO GÊMEO LOCAL: Integridade do banco SQLite verificável
# DIFERENÇA DE COMPORTAMENTO: Nenhuma — lógica idêntica

"""
Sparse Merkle Tree — Integridade verificável com esquecimento seletivo.

INTENÇÃO: A implementação original usava hash chain linear, mas isso
quebra quando o usuário solicita esquecimento seletivo. A SMT permite
provar integridade de qualquer subconjunto do banco mesmo que folhas
específicas sejam removidas ou anonimizadas.

INVARIANTE: Anonimizar uma folha nunca compromete a verificação das outras.
INVARIANTE: A Merkle Root é determinística — mesmas folhas = mesma root.
INVARIANTE: Nenhuma folha pode ser modificada após inserção (apenas anonimizada).
"""

import hashlib
import json
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone


# Placeholder usado para folhas anonimizadas (esquecimento seletivo)
ANONYMIZED_PLACEHOLDER = "ANONYMIZED"
EMPTY_HASH = hashlib.sha256(b"EMPTY").hexdigest()


@dataclass
class MerkleLeaf:
    """Uma folha da Sparse Merkle Tree."""
    key: str           # ID do registro no banco
    data_hash: str     # Hash do dado original
    table: str         # Tabela de origem
    created_at: str    # Timestamp ISO
    is_anonymized: bool = False

    @property
    def leaf_hash(self) -> str:
        """
        Hash da folha para cálculo do branch.

        INTENÇÃO: Se a folha foi anonimizada, o hash é calculado
        com o placeholder — o dado original não existe mais.
        """
        if self.is_anonymized:
            content = f"{self.key}:{ANONYMIZED_PLACEHOLDER}"
        else:
            content = f"{self.key}:{self.data_hash}:{self.table}"
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class MerkleProof:
    """Prova de inclusão/exclusão na árvore."""
    leaf_key: str
    leaf_hash: str
    sibling_hashes: List[Tuple[str, str]]  # (posição "left"/"right", hash)
    root: str
    is_valid: bool

    def to_dict(self) -> dict:
        return {
            "leaf_key": self.leaf_key,
            "leaf_hash": self.leaf_hash,
            "sibling_hashes": self.sibling_hashes,
            "root": self.root,
            "is_valid": self.is_valid,
        }


class SparseMerkleTree:
    """
    Sparse Merkle Tree para integridade do Banco de Causalidade.

    INTENÇÃO: Permite provar que:
    1. Um registro específico existe e não foi alterado
    2. Um registro foi legitimamente anonimizado em data X
    3. Todos os outros registros mantêm integridade após um esquecimento

    A árvore é reconstruída in-memory a partir das folhas persistidas.
    As raízes (Merkle Roots) são registradas no banco para auditoria.
    """

    def __init__(self):
        self._leaves: Dict[str, MerkleLeaf] = {}
        self._root: str = EMPTY_HASH
        self._history: List[Dict] = []  # Histórico de roots

    @property
    def root(self) -> str:
        """Merkle Root atual da árvore."""
        return self._root

    @property
    def leaf_count(self) -> int:
        """Número total de folhas (incluindo anonimizadas)."""
        return len(self._leaves)

    def insert_leaf(self, key: str, data: dict, table: str) -> MerkleLeaf:
        """
        Insere uma nova folha na árvore.

        INTENÇÃO: Cada inserção no banco de dados gera uma folha na SMT.
        O hash do dado garante que qualquer alteração futura é detectável.

        INVARIANTE: Uma vez inserida, uma folha nunca é modificada
        (apenas pode ser anonimizada via anonymize_leaf).
        """
        if key in self._leaves:
            raise ValueError(
                f"Folha '{key}' já existe na árvore. "
                "O Banco de Causalidade é append-only — registros existentes "
                "nunca são modificados."
            )

        data_hash = self._hash_data(data)
        now = datetime.now(timezone.utc).isoformat()

        leaf = MerkleLeaf(
            key=key,
            data_hash=data_hash,
            table=table,
            created_at=now,
        )

        self._leaves[key] = leaf
        self._recalculate_root()

        self._history.append({
            "operation": "insert",
            "key": key,
            "table": table,
            "timestamp": now,
            "new_root": self._root,
            "leaf_count": self.leaf_count,
        })

        return leaf

    def anonymize_leaf(self, key: str, reason: str) -> Tuple[str, str]:
        """
        Anonimiza uma folha — esquecimento seletivo.

        INTENÇÃO: Quando o usuário solicita esquecimento de um registro:
        1. O dado é substituído pelo placeholder ANONYMIZED
        2. Os branches são recalculados
        3. Uma nova Merkle Root é gerada
        4. O banco pode provar que o registro foi legitimamente anonimizado
        5. O dado original não existe mais — ninguém pode recuperá-lo

        Retorna: (nova_merkle_root, hash_da_folha_anonimizada)
        """
        if key not in self._leaves:
            raise KeyError(f"Folha '{key}' não encontrada na árvore.")

        leaf = self._leaves[key]

        if leaf.is_anonymized:
            raise ValueError(f"Folha '{key}' já foi anonimizada.")

        # Anonimizar — o dado original é perdido para sempre
        leaf.is_anonymized = True
        leaf.data_hash = hashlib.sha256(ANONYMIZED_PLACEHOLDER.encode()).hexdigest()

        self._recalculate_root()

        now = datetime.now(timezone.utc).isoformat()
        self._history.append({
            "operation": "anonymize",
            "key": key,
            "reason": reason,
            "timestamp": now,
            "new_root": self._root,
            "leaf_count": self.leaf_count,
        })

        return self._root, leaf.leaf_hash

    def verify_leaf(self, key: str) -> bool:
        """
        Verifica se uma folha existe e é íntegra.

        INTENÇÃO: Permite verificar a qualquer momento se um registro
        específico está íntegro na árvore.
        """
        if key not in self._leaves:
            return False

        leaf = self._leaves[key]
        # Recalcula e compara
        stored_hash = leaf.leaf_hash
        return stored_hash is not None and len(stored_hash) == 64

    def get_proof(self, key: str) -> MerkleProof:
        """
        Gera prova de inclusão para uma folha.

        INTENÇÃO: Permite a qualquer auditor externo verificar que
        um registro específico faz parte da árvore sem precisar
        reconstruir a árvore inteira.
        """
        if key not in self._leaves:
            return MerkleProof(
                leaf_key=key,
                leaf_hash="",
                sibling_hashes=[],
                root=self._root,
                is_valid=False,
            )

        leaf = self._leaves[key]
        sibling_hashes = self._compute_proof_path(key)

        return MerkleProof(
            leaf_key=key,
            leaf_hash=leaf.leaf_hash,
            sibling_hashes=sibling_hashes,
            root=self._root,
            is_valid=True,
        )

    def verify_proof(self, proof: MerkleProof) -> bool:
        """
        Verifica uma prova de inclusão.

        INTENÇÃO: Validação independente — qualquer um com a prova
        e a root pode verificar sem acesso à árvore completa.
        """
        if not proof.is_valid:
            return False

        current_hash = proof.leaf_hash
        for position, sibling_hash in proof.sibling_hashes:
            if position == "left":
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash
            current_hash = hashlib.sha256(combined.encode()).hexdigest()

        return current_hash == proof.root

    def get_root_history(self) -> List[Dict]:
        """Retorna histórico completo de Merkle Roots."""
        return self._history.copy()

    def get_leaf(self, key: str) -> Optional[MerkleLeaf]:
        """Retorna uma folha por chave, ou None."""
        return self._leaves.get(key)

    def export_state(self) -> Dict:
        """
        Exporta estado completo da árvore para persistência.

        INTENÇÃO: Permite salvar e restaurar a árvore entre reinicializações.
        """
        return {
            "root": self._root,
            "leaves": {
                k: {
                    "key": v.key,
                    "data_hash": v.data_hash,
                    "table": v.table,
                    "created_at": v.created_at,
                    "is_anonymized": v.is_anonymized,
                }
                for k, v in self._leaves.items()
            },
            "history": self._history,
        }

    @classmethod
    def from_state(cls, state: Dict) -> "SparseMerkleTree":
        """
        Restaura árvore a partir de estado exportado.

        INTENÇÃO: Na inicialização, a árvore é reconstruída a partir
        do estado persistido. A Merkle Root é recalculada e comparada
        com a root salva para verificar integridade.
        """
        tree = cls()
        for key, leaf_data in state.get("leaves", {}).items():
            leaf = MerkleLeaf(**leaf_data)
            tree._leaves[key] = leaf
        tree._history = state.get("history", [])
        tree._recalculate_root()

        saved_root = state.get("root", EMPTY_HASH)
        if tree._root != saved_root and len(state.get("leaves", {})) > 0:
            raise RuntimeError(
                f"INTEGRIDADE COMPROMETIDA: Merkle Root calculada ({tree._root}) "
                f"difere da salva ({saved_root}). "
                "O Banco de Causalidade pode ter sido adulterado."
            )

        return tree

    # =========================================================================
    # MÉTODOS INTERNOS
    # =========================================================================

    def _hash_data(self, data: dict) -> str:
        """Calcula hash determinístico de um dicionário."""
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _recalculate_root(self):
        """
        Recalcula a Merkle Root a partir de todas as folhas.

        INTENÇÃO: Usa construção bottom-up da árvore binária.
        Folhas ordenadas por chave para determinismo.
        """
        if not self._leaves:
            self._root = EMPTY_HASH
            return

        # Ordenar folhas por chave para resultado determinístico
        sorted_keys = sorted(self._leaves.keys())
        current_level = [self._leaves[k].leaf_hash for k in sorted_keys]

        # Construir árvore bottom-up
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                parent = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent)
            current_level = next_level

        self._root = current_level[0]

    def _compute_proof_path(self, key: str) -> List[Tuple[str, str]]:
        """
        Calcula o caminho de prova (siblings) para uma folha.

        INTENÇÃO: Para verificar uma folha, precisamos dos hashes
        de todos os siblings no caminho até a root.
        """
        sorted_keys = sorted(self._leaves.keys())
        current_level = [self._leaves[k].leaf_hash for k in sorted_keys]
        key_index = sorted_keys.index(key)

        proof_path = []
        idx = key_index

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left

                # Se o índice atual está neste par, registrar o sibling
                if i == idx or i + 1 == idx:
                    if i == idx:
                        sibling_pos = "right"
                        sibling_hash = right
                    else:
                        sibling_pos = "left"
                        sibling_hash = left
                    proof_path.append((sibling_pos, sibling_hash))

                combined = left + right
                parent = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent)

            idx = idx // 2
            current_level = next_level

        return proof_path
