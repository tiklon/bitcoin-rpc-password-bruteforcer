# Bruteforce Passwords to any Bitcoin Client
This project is a simple proof of work script for bruteforcing RPC passwords for Bitcoin clients.
It has these basic capabilities:
- check whether there is a Bitcoin RPC client listening behind a given IP address.
- try out passwords from a list to find the correct one
- parallelize all of these checks with bulk requests

## Results
Only a small number of nodes can be expected to be reachable via RPC at a given time, probably less than 10.
Out of these, we expect none to have a password out of the set of most common ones as they can be found in wellknown wordlists like rockyou.txt

## Countermeasures
Certain countermeasures are advised for Bitcoin Client operators to not be vulnerable to this kind of attack:
- Set a strong RPC password
- Configure the RPC client to accept only connections from IP ranges that you control

In fact, you should consider shutting down the RPC client altogether.
The RPC call is unencrypted and anyone along the way can listen to your password attempts.

## Why
We have observed this kind of attack to occur in the wild.
Our Bitcoin client logged a large number of incorrect RPC password attempts in a short time.
Out of curiosity we recreated this attack in a simple proof of work.

## Disclaimer
To run this script on Bitcoin Clients that you do not own can be illegal. 
We hereby declare specially that we refuse any responsibility for any damage caused by this script and reject any liability.
