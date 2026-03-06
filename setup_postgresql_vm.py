#!/usr/bin/env python3
"""
Script para configurar PostgreSQL na VM Debian
Executa os comandos de configuração remotamente via SSH
"""
import paramiko
import time

def setup_postgresql():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("Conectando à VM...")
    client.connect('192.168.100.20', username='rebeka', password='terremoto')
    
    # Verificar se PostgreSQL está rodando
    stdin, stdout, stderr = client.exec_command('systemctl is-active postgresql')
    status = stdout.read().decode().strip()
    print(f"PostgreSQL status: {status}")
    
    # Configurar listen_addresses
    print("Configurando listen_addresses...")
    stdin, stdout, stderr = client.exec_command(
        "sed -i \"s/#listen_addresses = 'localhost'/listen_addresses = '*'/\" /etc/postgresql/17/main/postgresql.conf"
    )
    
    # Adicionar regra de autenticação
    print("Adicionando regra de autenticação...")
    stdin, stdout, stderr = client.exec_command(
        "echo 'host all all 0.0.0.0/0 md5' >> /etc/postgresql/17/main/pg_hba.conf"
    )
    
    # Verificar configuração
    stdin, stdout, stderr = client.exec_command("grep listen_addresses /etc/postgresql/17/main/postgresql.conf")
    print(f"Configuração: {stdout.read().decode().strip()}")
    
    # Tentar reiniciar (pode falhar sem sudo)
    print("Tentando reiniciar PostgreSQL...")
    stdin, stdout, stderr = client.exec_command("pg_ctlcluster 17 main restart 2>&1 || true")
    result = stdout.read().decode().strip()
    print(f"Reiniciar: {result}")
    
    time.sleep(2)
    
    # Verificar portas
    stdin, stdout, stderr = client.exec_command("netstat -tlnp | grep 5432")
    ports = stdout.read().decode().strip()
    print(f"Portas: {ports}")
    
    # Testar conexão local
    stdin, stdout, stderr = client.exec_command("PGPASSWORD=terremoto psql -h localhost -U rebeka -d causal_bank -c 'SELECT 1'")
    test = stdout.read().decode().strip()
    print(f"Teste conexão local: {test[:50]}")
    
    client.close()
    print("\n✅ Configuração concluída!")
    print("Nota: Se a porta 5432 não aparecer em 0.0.0.0, a VM precisa de reinício manual com sudo.")

if __name__ == "__main__":
    setup_postgresql()
