#! /usr/bin/env python3
#

import sys
import asyncio
import argparse
import json
import datetime
from connectrum.client import StratumClient
from connectrum.svr_info import ServerInfo


class MyStratumClient(StratumClient):
    async def _keepalive(self):
        '''
            Override base method to use 'server.ping' method instead
            of 'server.version' to keep the connection alive.
        '''
        while self.protocol:
            await self.RPC('server.ping')
            await asyncio.sleep(120)  # Ping every two seconds


async def print_block_info(conn, blocks, last_time=None):
    time_recv = datetime.datetime.now()
    delta = (time_recv - last_time).total_seconds() if last_time else 0

    print('Block received at: {}'.format(time_recv))
    print('Delta (seconds): {}'.format(delta))

    if not isinstance(blocks, list):
        blocks = [blocks]
    for block in blocks:
        height = int(block['height'])
        coinbase_tx = await conn.RPC('blockchain.transaction.id_from_pos', height, 0)
        print('Height: {}'.format(height))
        print('Coinbase TX ID: {}'.format(coinbase_tx['txid']))

    print()

    return time_recv


async def listen(conn, svr, connector, verbose=False):
    method = 'blockchain.headers.subscribe'
    try:
        await connector
    except Exception as e:
        print("Unable to connect to server: %s" % e)
        return -1

    print("\nConnected to: %s\n" % svr)

    ack = await conn.RPC('server.version', 'Electrum 1.9.5', '1.4.1')
    print('Server version acknowledge: ' + repr(ack))

    banner = await conn.RPC('server.banner')
    print('\n---\n{}\n---'.format(banner))

    # Subscribe to new block events
    future, queue = conn.subscribe(method)

    block = await future
    time_recv = await print_block_info(conn, block)
    while True:
        block = await queue.get()
        time_recv = await print_block_info(conn, block, time_recv)


def main():
    parser = argparse.ArgumentParser(description='Subscribe to BTC events')
    parser.add_argument('server',
                        help='Hostname of ElectrumX server to use')
    parser.add_argument('--port', default=None,
                        help='Port number to override default for protocol')

    args = parser.parse_args()

    svr = ServerInfo(args.server, args.server,
                     ports=('t'+args.port))

    loop = asyncio.get_event_loop()

    conn = MyStratumClient()
    connector = conn.connect(
        svr, use_tor=False, disable_cert_verify=True)

    loop.run_until_complete(
        listen(conn, svr, connector))

    loop.close()


if __name__ == '__main__':
    main()
