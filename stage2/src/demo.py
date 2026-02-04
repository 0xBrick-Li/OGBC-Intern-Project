"""
Stage 2 Demo Script

演示和验证 Stage 2 索引器的功能。
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from web3 import Web3

from src.db.schema import init_db, reset_db
from src.indexer.discovery import discover_markets
from src.indexer.run import run_indexer, index_single_transaction


def main():
    parser = argparse.ArgumentParser(description="Stage 2 Indexer Demo")
    
    # 数据源选项
    parser.add_argument("--tx-hash", help="Index a specific transaction")
    parser.add_argument("--from-block", type=int, help="Start block for indexing")
    parser.add_argument("--to-block", type=int, help="End block for indexing")
    
    # 事件/市场选项
    parser.add_argument("--event-slug", required=True, help="Event slug for market discovery")
    
    # 数据库选项
    parser.add_argument("--db", default="./data/demo_indexer.db", help="Database file path")
    parser.add_argument("--reset-db", action="store_true", help="Reset database before running")
    
    # 输出选项
    parser.add_argument("--output", help="Output JSON file path")
    
    args = parser.parse_args()
    
    # 加载环境变量
    load_dotenv()
    
    # 检查 RPC_URL
    rpc_url = os.getenv("RPC_URL")
    if not rpc_url:
        print("Error: RPC_URL not set in .env file")
        sys.exit(1)
    
    # 初始化 Web3
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    # 添加 POA 中间件（Polygon 需要）
    from web3.middleware import ExtraDataToPOAMiddleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    if not w3.is_connected():
        print("Error: Cannot connect to RPC")
        sys.exit(1)
    
    print(f"Connected to RPC: {rpc_url[:50]}...")
    
    # 初始化数据库
    if args.reset_db:
        print(f"Resetting database: {args.db}")
        conn = reset_db(args.db)
    else:
        print(f"Using database: {args.db}")
        conn = init_db(args.db)
    
    # 任务 A: Market Discovery
    print(f"\n=== Task A: Market Discovery ===")
    print(f"Event slug: {args.event_slug}")
    
    discovery_result = discover_markets(
        conn=conn,
        event_slug=args.event_slug,
        validate_tokens=True
    )
    
    print(f"Discovered {discovery_result['total_markets']} markets")
    print(f"Validated {discovery_result['validated_markets']} markets")
    if discovery_result['failed_validation']:
        print(f"Failed validation: {discovery_result['failed_validation']}")
    
    # 任务 B: Trades Indexer
    print(f"\n=== Task B: Trades Indexer ===")
    
    if args.tx_hash:
        # 索引单个交易
        print(f"Indexing transaction: {args.tx_hash}")
        indexer_result = index_single_transaction(
            w3=w3,
            conn=conn,
            tx_hash=args.tx_hash
        )
    elif args.from_block and args.to_block:
        # 索引区块范围
        print(f"Indexing blocks {args.from_block} to {args.to_block}")
        indexer_result = run_indexer(
            w3=w3,
            conn=conn,
            from_block=args.from_block,
            to_block=args.to_block
        )
    else:
        print("Warning: No tx-hash or block range specified, skipping trade indexing")
        indexer_result = None
    
    if indexer_result:
        print(f"Processed {indexer_result['total_logs']} logs")
        print(f"Inserted {indexer_result['inserted_trades']} trades")
        print(f"Skipped {indexer_result['skipped_trades']} trades (no matching market)")
    
    # 构建输出结果
    output_data = {
        "stage2": {
            "market_discovery": {
                "event_slug": discovery_result['event_slug'],
                "event_id": discovery_result['event_id'],
                "total_markets": discovery_result['total_markets'],
                "validated_markets": discovery_result['validated_markets']
            }
        }
    }
    
    if indexer_result:
        # 获取第一个市场的信息（用于显示）
        first_market = None
        if discovery_result['markets']:
            first_market = discovery_result['markets'][0]
        
        output_data["stage2"]["trades_indexer"] = {
            "from_block": indexer_result['from_block'],
            "to_block": indexer_result['to_block'],
            "inserted_trades": indexer_result['inserted_trades'],
            "market_slug": first_market['slug'] if first_market else None,
            "market_id": first_market['market_id'] if first_market else None,
            "sample_trades": indexer_result['sample_trades'],
            "db_path": args.db
        }
    
    # 输出结果
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nResults saved to: {args.output}")
    else:
        print("\n=== Results ===")
        print(json.dumps(output_data, indent=2))
    
    # 关闭数据库连接
    conn.close()
    
    print("\n=== Demo Complete ===")
    print(f"Database: {args.db}")
    print(f"To query the API, run:")
    print(f"  python -m src.api.server --db {args.db} --port 8000")


if __name__ == "__main__":
    main()
