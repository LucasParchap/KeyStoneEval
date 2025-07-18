#!/bin/bash
# Allow traffic from the subnet
iptables -A INPUT -s 192.169.100.0/24 -p tcp --dport 5000 -j ACCEPT
iptables -A INPUT -p tcp --dport 5000 -j DROP
