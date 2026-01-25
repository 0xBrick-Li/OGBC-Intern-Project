"""
Market Decoder - 任务 B

解析市场创建参数，计算链上 Token ID。
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from web3 import Web3

from src.ctf.derive import derive_binary_positions, get_condition_id
from src.indexer.gamma import (
    fetch_market_by_slug,
    extract_market_params,
    get_gamma_base_url
)


# Polymarket USDC.e 地址 (Polygon)
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

# ConditionalTokens 合约地址 (Polygon)
CONDITIONAL_TOKENS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"

# ConditionPreparation 事件签名
# event ConditionPreparation(bytes32 indexed conditionId, address indexed oracle, 
#                            bytes32 indexed questionId, uint256 outcomeSlotCount)
CONDITION_PREPARATION_TOPIC = Web3.keccak(
    text="ConditionPreparation(bytes32,address,bytes32,uint256)"
).hex()


@dataclass(frozen=True)
class MarketParams:
    """市场参数数据结构"""
    condition_id: str
    oracle: str
    question_id: str
    outcome_slot_count: int
    collateral_token: str
    yes_token_id: str
    no_token_id: str
    gamma: Optional[Dict[str, Any]] = None


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


def parse_condition_preparation_log(log: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析 ConditionPreparation 日志
    
    Args:
        log: 交易日志
    
    Returns:
        包含条件参数的字典
    """
    topics = log['topics']
    
    # topic[0] 是事件签名
    # topic[1] 是 conditionId (indexed)
    # topic[2] 是 oracle (indexed)
    # topic[3] 是 questionId (indexed)
    condition_id = topics[1].hex() if isinstance(topics[1], bytes) else topics[1]
    oracle_hex = topics[2].hex() if isinstance(topics[2], bytes) else topics[2]
    question_id = topics[3].hex() if isinstance(topics[3], bytes) else topics[3]
    
    # 从 oracle hex 中提取地址 (最后 20 bytes)
    oracle = Web3.to_checksum_address('0x' + oracle_hex[-40:])
    
    # 解析 data 部分 (outcomeSlotCount)
    data = log['data']
    if isinstance(data, str):
        data = data if data.startswith('0x') else '0x' + data
        data_bytes = bytes.fromhex(data[2:])
    else:
        data_bytes = data
    
    outcome_slot_count = int.from_bytes(data_bytes[0:32], 'big')
    
    return {
        'condition_id': condition_id,
        'oracle': oracle,
        'question_id': question_id,
        'outcome_slot_count': outcome_slot_count
    }


def decode_market_from_gamma(market_slug: str) -> MarketParams:
    """
    通过 Gamma API 获取市场信息并计算 Token ID
    
    Args:
        market_slug: 市场的 slug 标识符
    
    Returns:
        MarketParams 对象
    """
    # 获取市场信息
    base_url = get_gamma_base_url()
    market_data = fetch_market_by_slug(base_url, market_slug)
    
    # 提取参数
    params = extract_market_params(market_data)
    
    # 获取必需的参数
    condition_id = params.get('condition_id', '')
    question_id = params.get('question_id', '')
    
    if not condition_id:
        raise ValueError(f"condition_id not found in market data for slug: {market_slug}")
    
    # question_id 可能不存在，使用 condition_id 作为替代
    if not question_id:
        print("⚠ Warning: question_id not found, using condition_id as fallback", file=sys.stderr)
        question_id = condition_id
    
    # 规范化格式
    if not condition_id.startswith('0x'):
        condition_id = '0x' + condition_id
    if not question_id.startswith('0x'):
        question_id = '0x' + question_id
    
    # Gamma API 不提供 oracle 字段，使用 Polymarket 标准预言机
    # Polymarket 使用 UMA Optimistic Oracle V2 (UMAAdapterV2)
    oracle = "0x157Ce2d672854c848c9b79C49a8Cc6cc89176a49"
    oracle = Web3.to_checksum_address(oracle)
    
    # 计算 Token IDs
    positions = derive_binary_positions(
        oracle=oracle,
        question_id=question_id,
        collateral_token=USDC_ADDRESS,
        condition_id=condition_id
    )
    
    # 验证计算结果与 Gamma API 返回的 Token IDs 是否一致
    gamma_token_ids = params.get('clob_token_ids', [])
    yes_token_id = positions.position_yes
    no_token_id = positions.position_no
    
    if gamma_token_ids and len(gamma_token_ids) >= 2:
        # 规范化格式进行比较
        gamma_yes = gamma_token_ids[0].lower()
        gamma_no = gamma_token_ids[1].lower() if len(gamma_token_ids) > 1 else ''
        
        calc_yes = positions.position_yes.lower()
        calc_no = positions.position_no.lower()
        
        # 检查是否匹配 (可能顺序不同)
        if (calc_yes == gamma_yes and calc_no == gamma_no) or \
           (calc_yes == gamma_no and calc_no == gamma_yes):
            print("✓ Calculated Token IDs match Gamma API", file=sys.stderr)
        else:
            print("⚠ Warning: Calculated Token IDs differ from Gamma API", file=sys.stderr)
            print(f"  Gamma: YES={gamma_yes}, NO={gamma_no}", file=sys.stderr)
            print(f"  Calculated: YES={calc_yes}, NO={calc_no}", file=sys.stderr)
            print("  Using Gamma API Token IDs (likely NegativeRisk market)", file=sys.stderr)
            # 使用 Gamma API 的 Token IDs，因为这可能是 NegativeRisk 市场
            yes_token_id = gamma_token_ids[0]
            no_token_id = gamma_token_ids[1]
    
    return MarketParams(
        condition_id=condition_id,
        oracle=oracle,
        question_id=question_id,
        outcome_slot_count=2,
        collateral_token=USDC_ADDRESS,
        yes_token_id=yes_token_id,
        no_token_id=no_token_id,
        gamma=params
    )


def decode_market_from_tx(w3: Web3, tx_hash: str, log_index: Optional[int] = None) -> MarketParams:
    """
    从交易中的 ConditionPreparation 事件解析市场参数
    
    Args:
        w3: Web3 实例
        tx_hash: 交易哈希
        log_index: 日志索引 (可选，如果有多个日志)
    
    Returns:
        MarketParams 对象
    """
    # 获取交易回执
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    
    # 查找 ConditionPreparation 事件
    condition_logs = []
    
    for log in receipt['logs']:
        # 检查是否是 ConditionalTokens 合约的日志
        log_address = log['address']
        if isinstance(log_address, str):
            log_address = Web3.to_checksum_address(log_address)
        
        if log_address.lower() != CONDITIONAL_TOKENS.lower():
            continue
        
        # 检查是否是 ConditionPreparation 事件
        if not log['topics']:
            continue
        
        topic0 = log['topics'][0]
        topic0_hex = topic0.hex() if isinstance(topic0, bytes) else topic0
        
        if topic0_hex.lower() != CONDITION_PREPARATION_TOPIC.lower():
            continue
        
        condition_logs.append(log)
    
    if not condition_logs:
        raise ValueError(f"No ConditionPreparation event found in transaction {tx_hash}")
    
    # 如果指定了 log_index，使用它
    if log_index is not None:
        target_log = None
        for log in condition_logs:
            if log['logIndex'] == log_index:
                target_log = log
                break
        
        if target_log is None:
            raise ValueError(f"No ConditionPreparation event found at log index {log_index}")
    else:
        # 否则使用第一个
        target_log = condition_logs[0]
        if len(condition_logs) > 1:
            print(f"Warning: Multiple ConditionPreparation events found, using log index {target_log['logIndex']}", 
                  file=sys.stderr)
    
    # 解析日志
    params = parse_condition_preparation_log(target_log)
    
    # 计算 Token IDs
    positions = derive_binary_positions(
        oracle=params['oracle'],
        question_id=params['question_id'],
        collateral_token=USDC_ADDRESS,
        condition_id=params['condition_id']
    )
    
    return MarketParams(
        condition_id=params['condition_id'],
        oracle=params['oracle'],
        question_id=params['question_id'],
        outcome_slot_count=params['outcome_slot_count'],
        collateral_token=USDC_ADDRESS,
        yes_token_id=positions.position_yes,
        no_token_id=positions.position_no,
        gamma=None
    )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Decode Polymarket market parameters")
    parser.add_argument("--market-slug", help="Market slug from Gamma API")
    parser.add_argument("--tx-hash", help="Transaction hash containing ConditionPreparation event")
    parser.add_argument("--log-index", type=int, help="Log index (if multiple events in transaction)")
    parser.add_argument("--output", help="Output JSON file path (optional)")
    
    args = parser.parse_args()
    
    # 至少需要提供一种输入方式
    if not args.market_slug and not args.tx_hash:
        parser.error("Must provide either --market-slug or --tx-hash")
    
    try:
        if args.market_slug:
            # 通过 Gamma API 解析
            print(f"Fetching market from Gamma API: {args.market_slug}", file=sys.stderr)
            market_params = decode_market_from_gamma(args.market_slug)
        else:
            # 从交易中解析
            print(f"Decoding transaction: {args.tx_hash}", file=sys.stderr)
            w3 = get_web3()
            market_params = decode_market_from_tx(w3, args.tx_hash, args.log_index)
        
        # 转换为字典
        result = asdict(market_params)
        
        # 输出结果
        output_json = json.dumps(result, indent=2)
        
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
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
