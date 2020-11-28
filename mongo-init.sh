#!/bin/bash
set -e

mongo <<EOF
use cme_data
db.createUser({
  user:  '$DB_MONGO_STD_USERNAME',
  pwd: '$DB_MONGO_STD_PASSWORD',
  roles: [{
    role: 'readWrite',
    db: 'cme_data'
  }]
})
EOF