#!/bin/bash
# setup_postgresql.sh
# Execute este script na VM Debian como root

echo "=== Configurando PostgreSQL para aceitar conexões remotas ==="

# 1. Atualizar listen_addresses
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/17/main/postgresql.conf

# 2. Adicionar regra de autenticação
echo "host all all 0.0.0.0/0 md5" >> /etc/postgresql/17/main/pg_hba.conf

# 3. Reiniciar PostgreSQL
systemctl restart postgresql@17-main

# 4. Verificar
echo ""
echo "=== Verificando configuração ==="
netstat -tlnp | grep 5432
echo ""
echo "Testando conexão..."
PGPASSWORD=terremoto psql -h localhost -U rebeka -d causal_bank -c "SELECT 'Conexão OK!' as status"
