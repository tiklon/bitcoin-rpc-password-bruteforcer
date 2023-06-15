# Bitcoin Client RPC Password Bruteforce

## Description
This project is a script designed to perform a proof-of-work bruteforce attack on the RPC passwords of Bitcoin clients. It provides the following functionality

- Verify the presence of a Bitcoin RPC client behind a given IP address.
- Try different passwords from a given list to determine the correct one.
- Parallelise the password checks using bulk requests.

## Results
It is important to note that only a limited number of nodes are typically reachable via RPC at any given time, typically less than 10. Furthermore, it is highly unlikely that any of these nodes will have a password from the set of common passwords found in popular dictionaries such as rockyou.txt.

## Countermeasures
To ensure protection against this type of attack, operators of Bitcoin clients are strongly advised to implement the following countermeasures:

- Set a strong RPC password.
- Configure the RPC client to only accept connections from IP ranges under their control.

In addition, consider disabling the RPC client altogether, as the RPC call is unencrypted, meaning that anyone intercepting the communication can eavesdrop on password attempts.

## Purpose
The motivation behind this project stems from real-world observations of such attacks. Our bitcoin client experienced a significant number of incorrect RPC password attempts in a short period of time. Out of curiosity, we created this proof-of-work script to replicate and study the attack.

## Disclaimer
It is important to note that running this script on Bitcoin clients that you do not own may be illegal. Therefore, we explicitly declare that we are not responsible for any damage caused by the use of this script and we disclaim any liability in connection with it.
