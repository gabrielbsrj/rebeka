#!/bin/bash
sudo sed -i "s/.*listen_addresses.*/listen_addresses = '*'/" /etc/postgresql/17/main/postgresql.conf
sudo bash -c 'echo "host all all 0.0.0.0/0 md5" >> /etc/postgresql/17/main/pg_hba.conf'
sudo systemctl restart postgresql@17-main
sleep 2
ss -tlnp | grep 5432
