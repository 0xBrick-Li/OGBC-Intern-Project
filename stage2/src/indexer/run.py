"""
Trades Indexer - 任务 B

扫描链上交易日志并存储到数据库。
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from web3 import Web3
from web3.types import LogReceipt

from src.ctf.trade_decoder import decode_order_filled, ORDER_FILLED_TOPIC
from src.db.store import fetch_market_by_token_id, insert_trades, update_sync_state


# Polymarket 交易所合约地址
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"  # 普通二元市场
NEGRISK_CTF_EXCHANGE = "0xC5d563A36AE78145C45a50134d48A1215220f80a"  # 负风险市场


def get_block_timestamp(w3: Web3, block_number: int, cache: Dict[int, int]) -> int:
    """
    获取区块时间戳（带缓存）
    
    Args:
        w3: Web3 实例
        block_number: 区块号
        cache: 时间戳缓存字典
        
    Returns:
        时间戳（Unix 时间）
    """
    if block_number in cache:
        return cache[block_number]
    
    block = w3.eth.get_block(block_number)
    timestamp = block['timestamp']
    cache[block_number] = timestamp
    return timestamp


def format_timestamp(unix_timestamp: int) -> str:
    """
    格式化时间戳为 ISO 8601 格式
    
    Args:
        unix_timestamp: Unix 时间戳
        
    Returns:
        ISO 8601 格式的时间字符串
    """
    return datetime.utcfromtimestamp(unix_timestamp).strftime('%Y-%m-%dT%H:%M:%S')


def parse_trade_from_log(
    log: LogReceipt,
    timestamp: str,
    conn: sqlite3.Connection
) -> Optional[Dict[str, Any]]:
    """
    从日志解析交易信息
    
    Args:
        log: Web3 日志对象
        timestamp: 时间戳
        conn: 数据库连接
        
    Returns:
        交易信息字典，如果无法匹配市场则返回 None
    """
    # 解码日志
    trade = decode_order_filled(log)
    
    # 确定 token_id（交易的头寸 token）
    token_id = trade.token_id
    
    # 查找对应的市场
    market = fetch_market_by_token_id(conn, token_id)
    if not market:
        print(f"Warning: Cannot find market for token_id {token_id} in tx {trade.tx_hash}")
        return None
    
    # 确定 outcome（YES 或 NO）
    if token_id.lower() == market['yes_token_id'].lower():
        outcome = "YES"
    elif token_id.lower() == market['no_token_id'].lower():
        outcome = "NO"
    else:
        outcome = "UNKNOWN"
    
    # 构建交易记录
    trade_record = {
        'market_id': market['market_id'],
        'tx_hash': trade.tx_hash,
        'log_index': trade.log_index,
        'block_number': log['blockNumber'],
        'timestamp': timestamp,
        'exchange': trade.exchange,
        'order_hash': trade.order_hash,
        'maker': trade.maker,
        'taker': trade.taker,
        'side': trade.side,
        'outcome': outcome,
        'price': trade.price,
        'size': str(Decimal(trade.taker_amount if trade.side == "BUY" else trade.maker_amount) / Decimal(10**6)),
        'token_id': token_id,
        'maker_asset_id': trade.maker_asset_id,
        'taker_asset_id': trade.taker_asset_id,
        'maker_amount': trade.maker_amount,
        'taker_amount': trade.taker_amount,
        'fee': trade.fee
    }
    
    return trade_record


def fetch_logs(
    w3: Web3,
    from_block: int,
    to_block: int,
    exchange_addresses: List[str]
) -> List[LogReceipt]:
    """
    获取指定区块范围内的 OrderFilled 日志
    
    Args:
        w3: Web3 实例
        from_block: 起始区块
        to_block: 结束区块
        exchange_addresses: 交易所合约地址列表
        
    Returns:
        日志列表
    """
    logs = w3.eth.get_logs({
        'fromBlock': from_block,
        'toBlock': to_block,
        'address': exchange_addresses,
        'topics': [ORDER_FILLED_TOPIC]
    })
    
    return logs


def run_indexer(
    w3: Web3,
    conn: sqlite3.Connection,
    from_block: int,
    to_block: int,
    exchange_addresses: Optional[List[str]] = None,
    sync_state_key: str = "trade_indexer"
) -> Dict[str, Any]:
    """
    运行交易索引器（任务 B）
    
    Args:
        w3: Web3 实例
        conn: 数据库连接
        from_block: 起始区块
        to_block: 结束区块
        exchange_addresses: 交易所合约地址列表
        sync_state_key: 同步状态键
        
    Returns:
        索引结果字典
    """
    if exchange_addresses is None:
        exchange_addresses = [CTF_EXCHANGE, NEGRISK_CTF_EXCHANGE]
    
    # 获取日志
    print(f"Fetching logs from block {from_block} to {to_block}...")
    logs = fetch_logs(w3, from_block, to_block, exchange_addresses)
    print(f"Found {len(logs)} OrderFilled events")
    
    # 解析交易
    timestamp_cache = {}
    trades = []
    skipped = 0
    
    for log in logs:
        # 获取时间戳
        block_number = log['blockNumber']
        unix_timestamp = get_block_timestamp(w3, block_number, timestamp_cache)
        timestamp = format_timestamp(unix_timestamp)
        
        # 解析交易
        trade_record = parse_trade_from_log(log, timestamp, conn)
        if trade_record:
            trades.append(trade_record)
        else:
            skipped += 1
    
    # 批量插入交易
    inserted_count = insert_trades(conn, trades)
    
    # 更新同步状态
    update_sync_state(conn, sync_state_key, to_block)
    
    result = {
        'from_block': from_block,
        'to_block': to_block,
        'total_logs': len(logs),
        'parsed_trades': len(trades),
        'inserted_trades': inserted_count,
        'skipped_trades': skipped,
        'sample_trades': trades[:5] if trades else []
    }
    
    return result


def get_transaction_block(w3: Web3, tx_hash: str) -> int:
    """
    获取交易所在的区块号
    
    Args:
        w3: Web3 实例
        tx_hash: 交易哈希
        
    Returns:
        区块号
    """
    tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
    return tx_receipt['blockNumber']


def index_single_transaction(
    w3: Web3,
    conn: sqlite3.Connection,
    tx_hash: str,
    exchange_addresses: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    索引单个交易
    
    Args:
        w3: Web3 实例
        conn: 数据库连接
        tx_hash: 交易哈希
        exchange_addresses: 交易所合约地址列表
        
    Returns:
        索引结果字典
    """
    # 获取交易所在区块
    block_number = get_transaction_block(w3, tx_hash)
    
    # 索引该区块
    return run_indexer(
        w3=w3,
        conn=conn,
        from_block=block_number,
        to_block=block_number,
        exchange_addresses=exchange_addresses
    )


if __name__ == "__main__":
    # 测试交易索引
    import os
    from dotenv import load_dotenv
    from src.db.schema import init_db
    from src.indexer.discovery import discover_markets
    
    load_dotenv()
    
    # 初始化
    w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
    conn = init_db("./data/test_indexer.db")
    
    # 先发现市场
    print("Discovering markets...")
    discover_markets(
        conn=conn,
        event_slug="will-there-be-another-us-government-shutdown-by-january-31"
    )
    
    # 索引交易
    print("\nIndexing trades...")
    result = index_single_transaction(
        w3=w3,
        conn=conn,
        tx_hash="0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946"
    )
    
    print(f"\nIndexed {result['inserted_trades']} trades")
    if result['sample_trades']:
        print(f"Sample trade: {result['sample_trades'][0]}")
    
    conn.close()
