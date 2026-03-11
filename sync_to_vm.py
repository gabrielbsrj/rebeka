import paramiko
import os

def sync_folder(sftp, local_dir, remote_base):
    for root, dirs, files in os.walk(local_dir):
        rel_path = os.path.relpath(root, local_dir)
        if rel_path == '.':
            remote_dir = remote_base
        else:
            clean_path = rel_path.replace('\\', '/')
            remote_dir = remote_base + '/' + clean_path
        
        parts = remote_dir.split('/')
        path = ''
        for p in parts:
            if p:
                path += '/' + p
                try:
                    sftp.stat(path)
                except:
                    sftp.mkdir(path)
        
        for f in files:
            if f.endswith(('.py', '.html', '.css', '.js')):
                local_path = os.path.join(root, f)
                remote_path = remote_dir + '/' + f
                try:
                    sftp.put(local_path, remote_path)
                    print(f'Uploaded: {f}')
                except Exception as e:
                    print(f'Error {f}: {e}')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.100.20', username='rebeka', password='terremoto')
sftp = client.open_sftp()

print('Syncing agent folders...')
folders_to_sync = ['automation', 'core', 'infrastructure', 'intelligence', 'interfaces', 'local', 'memory', 'processors', 'sensors', 'vps']
for folder in folders_to_sync:
    print(f'Syncing {folder}...')
    sync_folder(sftp, f'agent/{folder}', f'/home/rebeka/rebeka2/agent/{folder}')

print('Syncing config and main files...')
sftp.put('agent/config/config.yaml', '/home/rebeka/rebeka2/agent/config/config.yaml')
print('Uploading requirements...')
sftp.put('agent/requirements.txt', '/home/rebeka/rebeka2/agent/requirements.txt')
sftp.put('agent/run_dashboard.py', '/home/rebeka/rebeka2/agent/run_dashboard.py')

print('Creating/Uploading VM-specific .env...')
vm_env_content = f"""DATABASE_URL=sqlite:///agent/causal_bank_dev.db
TWIN_TYPE=vps
OLLAMA_API_BASE=http://192.168.100.8:11434/v1
"""
with sftp.file('/home/rebeka/rebeka2/.env', 'w') as f:
    f.write(vm_env_content)

print('Restarting Dashboard on VM...')
try:
    # Tenta matar o processo anterior (pode falhar se não houver um rodando)
    client.exec_command('pkill -f run_dashboard.py')
    # Inicia o novo dashboard em background
    client.exec_command('cd /home/rebeka/rebeka2 && nohup python3 agent/run_dashboard.py > dashboard.log 2>&1 &')
    print('Dashboard restarted!')
except Exception as e:
    print(f'Warning: Could not restart dashboard automatically: {e}')

sftp.close()
client.close()
print('DONE!')
