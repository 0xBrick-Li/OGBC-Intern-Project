"""
Trade Decoder - 任务 A

解析 Polymarket 链上交易日志，还原交易详情。
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from web3 import Web3


# Polymarket 交易所合约地址
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"  # 普通二元市场
NEGRISK_CTF_EXCHANGE = "0xC5d563A36AE78145C45a50134d48A1215220f80a"  # 负风险市场

# OrderFilled 事件签名
# event OrderFilled(bytes32 indexed orderHash, address indexed maker, address indexed taker, 
#                   uint256 makerAssetId, uint256 takerAssetId, uint256 makerAmountFilled,
#                   uint256 takerAmountFilled, uint256 fee)
ORDER_FILLED_TOPIC = Web3.keccak(text="OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)").hex()


@dataclass(frozen=True)
class Trade:
    """交易数据结构"""
    tx_hash: str
    log_index: int
    exchange: str
    order_hash: str
    maker: str
    taker: str
    maker_asset_id: str
    taker_asset_id: str
    maker_amount: str
    taker_amount: str
    fee: str
    price: str
    token_id: str
    side: str


def get_web3() -> Web3:
    """创建 Web3 实例"""
    load_dotenv()
    rpc_url = os.getenv("RPC_URL")
    
    if not rpc_url:
        raise ValueError("RPC_URL not found in environment. Please set it in .env file")
    
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to RPC: {rpc_url}")
    
    return w3


def parse_order_filled_log(log: Dict[str, Any], exchange: str) -> Trade:
    """
    解析 OrderFilled 日志
    
    Args:
        log: 交易日志
        exchange: 交易所合约地址
    
    Returns:
        Trade 对象
    """
    # 提取 topics
    topics = log['topics']
    
    # topic[0] 是事件签名
    # topic[1] 是 orderHash (indexed)
    # topic[2] 是 maker (indexed)
    # topic[3] 是 taker (indexed)
    order_hash = topics[1].hex() if isinstance(topics[1], bytes) else topics[1]
    maker = Web3.to_checksum_address('0x' + topics[2].hex()[-40:] if isinstance(topics[2], bytes) else '0x' + topics[2][-40:])
    taker = Web3.to_checksum_address('0x' + topics[3].hex()[-40:] if isinstance(topics[3], bytes) else '0x' + topics[3][-40:])
    
    # 解析 data 部分 (非 indexed 参数)
    data = log['data']
    if isinstance(data, str):
        data = data if data.startswith('0x') else '0x' + data
        data_bytes = bytes.fromhex(data[2:])
    else:
        data_bytes = data
    
    # data 包含 5 个 uint256: makerAssetId, takerAssetId, makerAmountFilled, takerAmountFilled, fee
    # 每个 uint256 是 32 bytes
    maker_asset_id = int.from_bytes(data_bytes[0:32], 'big')
    taker_asset_id = int.from_bytes(data_bytes[32:64], 'big')
    maker_amount_filled = int.from_bytes(data_bytes[64:96], 'big')
    taker_amount_filled = int.from_bytes(data_bytes[96:128], 'big')
    fee = int.from_bytes(data_bytes[128:160], 'big')
    
    # 判断交易方向和计算价格
    # maker_asset_id == 0 表示 maker 出 USDC，买入 token (BUY)
    # taker_asset_id == 0 表示 taker 出 USDC，卖出 token (SELL)
    if maker_asset_id == 0:
        # maker 用 USDC 买 token
        side = "BUY"
        token_id = f"0x{taker_asset_id:064x}"
        # price = USDC / token
        if taker_amount_filled > 0:
            price = Decimal(maker_amount_filled) / Decimal(taker_amount_filled)
        else:
            price = Decimal(0)
    else:
        # maker 卖出 token，得到 USDC
        side = "SELL"
        token_id = f"0x{maker_asset_id:064x}"
        # price = USDC / token
        if maker_amount_filled > 0:
            price = Decimal(taker_amount_filled) / Decimal(maker_amount_filled)
        else:
            price = Decimal(0)
    
    # 格式化价格（保留合理精度）
    price_str = f"{price:.6f}".rstrip('0').rstrip('.')
    
    return Trade(
        tx_hash=log['transactionHash'].hex() if isinstance(log['transactionHash'], bytes) else log['transactionHash'],
        log_index=log['logIndex'],
        exchange=exchange,
        order_hash=order_hash,
        maker=maker,
        taker=taker,
        maker_asset_id=str(maker_asset_id),
        taker_asset_id=str(taker_asset_id),
        maker_amount=str(maker_amount_filled),
        taker_amount=str(taker_amount_filled),
        fee=str(fee),
        price=price_str,
        token_id=token_id,
        side=side
    )


def decode_transaction(w3: Web3, tx_hash: str) -> List[Trade]:
    """
    解码交易中的所有 OrderFilled 事件
    
    Args:
        w3: Web3 实例
        tx_hash: 交易哈希
    
    Returns:
        Trade 对象列表
    """
    # 获取交易回执
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    
    trades = []
    
    # 遍历所有日志
    for log in receipt['logs']:
        # 检查是否是 Polymarket 交易所的日志
        log_address = log['address']
        
        # 规范化地址格式
        if isinstance(log_address, str):
            log_address = Web3.to_checksum_address(log_address)
        
        exchange = None
        if log_address == Web3.to_checksum_address(CTF_EXCHANGE):
            exchange = CTF_EXCHANGE
        elif log_address == Web3.to_checksum_address(NEGRISK_CTF_EXCHANGE):
            exchange = NEGRISK_CTF_EXCHANGE
        
        if exchange is None:
            continue
        
        # 检查是否是 OrderFilled 事件
        if not log['topics']:
            continue
        
        topic0 = log['topics'][0]
        topic0_hex = topic0.hex() if isinstance(topic0, bytes) else topic0
        
        if topic0_hex.lower() != ORDER_FILLED_TOPIC.lower():
            continue
        
        # 过滤掉 taker == exchange 的重复日志
        topics = log['topics']
        taker_address = '0x' + (topics[3].hex()[-40:] if isinstance(topics[3], bytes) else topics[3][-40:])
        taker_address = Web3.to_checksum_address(taker_address)
        
        # 跳过 taker 是交易所合约自己的日志（避免重复计数）
        if taker_address.lower() == exchange.lower():
            continue
        
        # 解析日志
        try:
            trade = parse_order_filled_log(log, exchange)
            trades.append(trade)
        except Exception as e:
            print(f"Error parsing log at index {log['logIndex']}: {e}", file=sys.stderr)
            continue
    
    return trades


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Decode Polymarket trade transactions")
    parser.add_argument("--tx-hash", required=True, help="Transaction hash to decode")
    parser.add_argument("--output", help="Output JSON file path (optional)")
    
    args = parser.parse_args()
    
    try:
        # 创建 Web3 实例
        w3 = get_web3()
        
        # 解码交易
        print(f"Decoding transaction: {args.tx_hash}", file=sys.stderr)
        trades = decode_transaction(w3, args.tx_hash)
        
        if not trades:
            print(f"No OrderFilled events found in transaction {args.tx_hash}", file=sys.stderr)
            return
        
        print(f"Found {len(trades)} trade(s)", file=sys.stderr)
        
        # 转换为字典列表
        trades_dict = [asdict(trade) for trade in trades]
        
        # 输出结果
        output_json = json.dumps(trades_dict, indent=2)
        
        if args.output:
            # 创建输出目录
            os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
            
            with open(args.output, 'w') as f:
                f.write(output_json)
            print(f"Results written to {args.output}", file=sys.stderr)
        else:
            print(output_json)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
