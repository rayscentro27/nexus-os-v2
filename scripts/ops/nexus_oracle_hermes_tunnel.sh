#!/bin/zsh
set -eu
exec /usr/bin/ssh -N -T -o BatchMode=yes -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o TCPKeepAlive=yes \
  -o StrictHostKeyChecking=accept-new \
  -L 127.0.0.1:18642:127.0.0.1:8642 -i "$HOME/.ssh/oracle_vm" opc@161.153.40.41
