#!/bin/bash
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/17/main/postgresql.conf
echo "host all all 0.0.0.0/0 md5" >> /etc/postgresql/17/main/pg_hba.conf
systemctl restart postgresql@17-main
sleep 2
netstat -tlnp | grep 5432
