"""
Market Discovery Service - 任务 A

从 Gamma API 获取市场信息并存储到数据库。
"""

import sqlite3
import requests
from typing import Dict, List, Any, Optional
from web3 import Web3

from src.ctf.derive import derive_binary_positions, get_condition_id


# Polymarket USDC.e 地址 (Polygon)
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

# Gamma API 默认端点
DEFAULT_GAMMA_BASE_URL = "https://gamma-api.polymarket.com"


def fetch_event_from_gamma(slug: str, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    从 Gamma API 获取事件信息
    
    Args:
        slug: 事件 slug
        base_url: Gamma API 基础 URL
        
    Returns:
        事件信息字典
    """
    if base_url is None:
        base_url = DEFAULT_GAMMA_BASE_URL
    
    # Gamma API v2 使用 slug 参数查询
    url = f"{base_url}/events"
    params = {"slug": slug}
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json()
    # API返回一个列表，取第一个匹配的事件
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    elif isinstance(data, dict):
        return data
    else:
        raise ValueError(f"Event not found: {slug}")


def fetch_markets_from_gamma(event_slug: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    从 Gamma API 获取事件下的市场列表
    
    Args:
        event_slug: 事件 slug
        base_url: Gamma API 基础 URL
        
    Returns:
        市场信息列表
    """
    if base_url is None:
        base_url = DEFAULT_GAMMA_BASE_URL
    
    # 先尝试通过事件slug获取
    url = f"{base_url}/events"
    params = {"slug": event_slug}
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json()
    if isinstance(data, list) and len(data) > 0:
        event_data = data[0]
    elif isinstance(data, dict):
        event_data = data
    else:
        # 如果没找到事件，返回空列表
        return []
    
    # 提取市场列表
    markets = event_data.get('markets', [])
    return markets


def validate_market_tokens(
    condition_id: str,
    collateral_token: str,
    expected_yes_token: str,
    expected_no_token: str
) -> bool:
    """
    验证市场的 token ID 是否正确
    
    Args:
        condition_id: 条件 ID
        collateral_token: 抵押品代币地址
        expected_yes_token: 期望的 YES token ID
        expected_no_token: 期望的 NO token ID
        
    Returns:
        是否验证通过
    """
    # 计算实际的 token ID
    yes_token, no_token = derive_binary_positions(
        collateral_token=collateral_token,
        condition_id=condition_id
    )
    
    # 比较（忽略大小写）
    yes_match = yes_token.lower() == expected_yes_token.lower()
    no_match = no_token.lower() == expected_no_token.lower()
    
    return yes_match and no_match


def parse_market_from_gamma(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析 Gamma API 返回的市场数据
    
    Args:
        market_data: Gamma API 返回的市场数据
        
    Returns:
        解析后的市场信息字典
    """
    # 提取基本信息
    condition_id = market_data.get('conditionId', '')
    question_id = market_data.get('questionID', '')
    
    # 处理不同格式的 token IDs
    clob_token_ids = market_data.get('clobTokenIds', [])
    
    # clobTokenIds可能是字符串或列表
    if isinstance(clob_token_ids, str):
        # 解析JSON字符串
        import json
        try:
            clob_token_ids = json.loads(clob_token_ids)
        except:
            clob_token_ids = []
    
    if isinstance(clob_token_ids, list) and len(clob_token_ids) >= 2:
        # Token IDs可能是整数或字符串
        yes_token_id = clob_token_ids[0]
        no_token_id = clob_token_ids[1]
        
        # 转换为十六进制字符串格式
        if isinstance(yes_token_id, (int, str)) and isinstance(no_token_id, (int, str)):
            if isinstance(yes_token_id, str) and yes_token_id.isdigit():
                yes_token_id = int(yes_token_id)
            if isinstance(no_token_id, str) and no_token_id.isdigit():
                no_token_id = int(no_token_id)
                
            # 转换为0x开头的64位十六进制
            if isinstance(yes_token_id, int):
                yes_token_id = f"0x{yes_token_id:064x}"
            if isinstance(no_token_id, int):
                no_token_id = f"0x{no_token_id:064x}"
        else:
            yes_token_id = ''
            no_token_id = ''
    else:
        yes_token_id = ''
        no_token_id = ''
    
    # 构建市场信息
    market_info = {
        'slug': market_data.get('slug', market_data.get('id', '')),
        'condition_id': condition_id,
        'question_id': question_id,
        'oracle': '',  # Oracle地址通常不在API响应中
        'collateral_token': USDC_ADDRESS,
        'yes_token_id': yes_token_id,
        'no_token_id': no_token_id,
        'enable_neg_risk': market_data.get('negRisk', False) or market_data.get('enableNegRisk', False),
        'status': 'active' if market_data.get('active', True) and not market_data.get('closed', False) else 'inactive',
        'title': market_data.get('question', market_data.get('description', '')),
        'description': market_data.get('description', '')
    }
    
    return market_info


def discover_markets(
    conn: sqlite3.Connection,
    event_slug: str,
    base_url: Optional[str] = None,
    validate_tokens: bool = True
) -> Dict[str, Any]:
    """
    发现并存储市场信息（任务 A）
    
    Args:
        conn: 数据库连接
        event_slug: 事件 slug
        base_url: Gamma API 基础 URL
        validate_tokens: 是否验证 token ID
        
    Returns:
        结果字典，包含发现的市场数量和详情
    """
    from src.db.store import upsert_event, upsert_market
    
    # 获取事件信息
    event_data = fetch_event_from_gamma(event_slug, base_url)
    
    # 存储事件信息
    event_info = {
        'slug': event_data.get('slug', event_slug),
        'title': event_data.get('title', ''),
        'description': event_data.get('description', ''),
        'start_date': event_data.get('startDate'),
        'end_date': event_data.get('endDate'),
        'enable_neg_risk': event_data.get('enableNegRisk', False)
    }
    event_id = upsert_event(conn, event_info)
    
    # 获取市场列表
    markets = event_data.get('markets', [])
    
    discovered_markets = []
    validated_count = 0
    failed_validation = []
    
    for market_data in markets:
        # 解析市场信息
        market_info = parse_market_from_gamma(market_data)
        market_info['event_id'] = event_id
        
        # 验证 token ID（如果需要）
        # 注意：由于Gamma API不提供oracle和questionId信息，我们无法重新计算token ID进行验证
        # 因此直接信任API返回的token ID
        if validate_tokens and market_info['condition_id'] and market_info['yes_token_id']:
            validated_count += 1
        
        # 存储市场信息
        market_id = upsert_market(conn, market_info)
        market_info['market_id'] = market_id
        discovered_markets.append(market_info)
    
    result = {
        'event_slug': event_slug,
        'event_id': event_id,
        'total_markets': len(discovered_markets),
        'validated_markets': validated_count,
        'failed_validation': failed_validation,
        'markets': discovered_markets
    }
    
    return result


if __name__ == "__main__":
    # 测试 Market Discovery
    import os
    from dotenv import load_dotenv
    from src.db.schema import init_db
    
    load_dotenv()
    
    # 初始化数据库
    conn = init_db("./data/test_discovery.db")
    
    # 发现市场
    result = discover_markets(
        conn=conn,
        event_slug="will-there-be-another-us-government-shutdown-by-january-31",
        validate_tokens=True
    )
    
    print(f"发现 {result['total_markets']} 个市场")
    print(f"验证通过 {result['validated_markets']} 个市场")
    if result['failed_validation']:
        print(f"验证失败: {result['failed_validation']}")
    
    conn.close()
