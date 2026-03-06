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

print('Syncing shared...')
sync_folder(sftp, 'agent/shared', '/home/rebeka/rebeka2/agent/shared')

print('Syncing vps...')
sync_folder(sftp, 'agent/vps', '/home/rebeka/rebeka2/agent/vps')

print('Syncing config...')
sftp.put('agent/config/config.yaml', '/home/rebeka/rebeka2/agent/config/config.yaml')

print('Syncing requirements...')
sftp.put('agent/requirements.txt', '/home/rebeka/rebeka2/agent/requirements.txt')

sftp.close()
client.close()
print('DONE!')
