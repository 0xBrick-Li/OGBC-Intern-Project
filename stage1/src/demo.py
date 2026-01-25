"""
综合演示脚本

同时执行交易解析和市场解码，展示完整的链上数据解析流程。
"""

import argparse
import json
import os
import sys
from dataclasses import asdict
from typing import Dict, Any

from dotenv import load_dotenv

from src.trade_decoder import get_web3, decode_transaction
from src.market_decoder import decode_market_from_gamma


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Polymarket Stage 1 Comprehensive Demo"
    )
    parser.add_argument(
        "--tx-hash",
        required=True,
        help="Transaction hash to decode trades"
    )
    parser.add_argument(
        "--event-slug",
        required=True,
        help="Event slug from Gamma API"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path (optional)"
    )
    
    args = parser.parse_args()
    
    try:
        load_dotenv()
        
        # 获取 Web3 实例
        w3 = get_web3()
        
        print("=" * 60, file=sys.stderr)
        print("Polymarket Stage 1 Demo", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        
        # 1. 解码交易
        print(f"\n[1/2] Decoding transaction: {args.tx_hash}", file=sys.stderr)
        trades = decode_transaction(w3, args.tx_hash)
        print(f"✓ Found {len(trades)} trade(s)", file=sys.stderr)
        
        # 2. 解码市场
        print(f"\n[2/2] Fetching market from Gamma API: {args.event_slug}", file=sys.stderr)
        market_params = decode_market_from_gamma(args.event_slug)
        print(f"✓ Market decoded successfully", file=sys.stderr)
        print(f"  Condition ID: {market_params.condition_id[:10]}...", file=sys.stderr)
        print(f"  Oracle: {market_params.oracle}", file=sys.stderr)
        print(f"  YES Token: {market_params.yes_token_id[:10]}...", file=sys.stderr)
        print(f"  NO Token: {market_params.no_token_id[:10]}...", file=sys.stderr)
        
        # 3. 匹配交易和市场
        print(f"\n[3/3] Matching trades with market", file=sys.stderr)
        matched_trades = []
        unmatched_trades = []
        
        for trade in trades:
            token_id_lower = trade.token_id.lower()
            yes_token_lower = market_params.yes_token_id.lower()
            no_token_lower = market_params.no_token_id.lower()
            
            if token_id_lower == yes_token_lower:
                matched_trades.append((trade, "YES"))
                print(f"  ✓ Trade {trade.log_index}: YES token @ {trade.price}", file=sys.stderr)
            elif token_id_lower == no_token_lower:
                matched_trades.append((trade, "NO"))
                print(f"  ✓ Trade {trade.log_index}: NO token @ {trade.price}", file=sys.stderr)
            else:
                unmatched_trades.append(trade)
                print(f"  ✗ Trade {trade.log_index}: Unmatched token", file=sys.stderr)
        
        # 4. 构建输出
        result = {
            "stage1": {
                "tx_hash": args.tx_hash,
                "event_slug": args.event_slug,
                "summary": {
                    "total_trades": len(trades),
                    "matched_trades": len(matched_trades),
                    "unmatched_trades": len(unmatched_trades)
                },
                "trades": [
                    {
                        **asdict(trade),
                        "matched_outcome": outcome if any(t[0] == trade for t in matched_trades) else None
                    }
                    for trade in trades
                    for outcome in [next((o for t, o in matched_trades if t == trade), None)]
                ],
                "market": asdict(market_params)
            }
        }
        
        # 5. 输出结果
        output_json = json.dumps(result, indent=2)
        
        if args.output:
            os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
            with open(args.output, 'w') as f:
                f.write(output_json)
            print(f"\n✓ Results written to {args.output}", file=sys.stderr)
        else:
            print("\n" + "=" * 60, file=sys.stderr)
            print("Output:", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print(output_json)
        
        print("\n" + "=" * 60, file=sys.stderr)
        print("Demo completed successfully!", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
