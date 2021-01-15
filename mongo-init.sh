#!/bin/bash
set -e

mongo <<EOF
use cme_data
db.createUser({
  user:  '$CME_DB_USERNAME',
  pwd: '$CME_DB_PASSWORD',
  roles: [{
    role: 'readWrite',
    db: '$CME_DB_NAME'
  }]
})
EOF