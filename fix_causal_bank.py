import re

with open('agent/shared/database/causal_bank.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace any: leaf_hash = self._smt.insert_leaf(record_id, leaf_data, "...")
# with:
# leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "...")
# leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)

new_content = re.sub(
    r'leaf_hash\s*=\s*self\._smt\.insert_leaf\(([^)]+)\)',
    r"leaf_obj = self._smt.insert_leaf(\g<1>)\n            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)",
    content
)

with open('agent/shared/database/causal_bank.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
    print("Fix applied to causal_bank.py")
