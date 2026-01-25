"""
Polymarket Gamma API Client

提供与 Polymarket Gamma API 交互的功能，用于获取市场和事件的元数据。
"""

import requests
from typing import Optional, Dict, Any, List
import os


# Gamma API 默认端点
DEFAULT_GAMMA_BASE_URL = "https://gamma-api.polymarket.com"


def get_gamma_base_url() -> str:
    """获取 Gamma API 基础 URL"""
    return os.getenv("GAMMA_API_BASE_URL", DEFAULT_GAMMA_BASE_URL)


def fetch_event_by_slug(base_url: Optional[str], slug: str) -> Dict[str, Any]:
    """
    通过 slug 获取事件信息
    
    Args:
        base_url: Gamma API 基础 URL (如果为 None，使用默认值)
        slug: 事件的 slug 标识符
    
    Returns:
        事件信息的字典
    
    Raises:
        requests.HTTPError: 当请求失败时
    """
    if base_url is None:
        base_url = get_gamma_base_url()
    
    url = f"{base_url}/events/{slug}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_market_by_slug(base_url: Optional[str], slug: str) -> Dict[str, Any]:
    """
    通过 slug 或 ID 获取市场信息
    
    Args:
        base_url: Gamma API 基础 URL (如果为 None，使用默认值)
        slug: 市场的 slug 标识符或 ID
    
    Returns:
        市场信息的字典
    
    Raises:
        requests.HTTPError: 当请求失败时
    """
    if base_url is None:
        base_url = get_gamma_base_url()
    
    # Gamma API 的 /markets/{id} 端点使用的是 ID，不是slug
    # 如果传入的看起来像数字 ID，直接使用
    # 否则假定是 slug，需要先查找对应的 ID
    url = f"{base_url}/markets/{slug}"
    response = requests.get(url)
    
    # 如果失败且不是纯数字，可能是 slug，尝试搜索
    if response.status_code == 422 and not slug.isdigit():
        # 尝试从市场列表中搜索
        try:
            markets_response = requests.get(f"{base_url}/markets", params={'limit': 100})
            if markets_response.status_code == 200:
                markets = markets_response.json()
                for market in markets:
                    if market.get('slug') == slug:
                        return market
        except:
            pass
    
    response.raise_for_status()
    return response.json()


def fetch_market_by_condition_or_tokens(
    base_url: Optional[str],
    condition_id: Optional[str] = None,
    token_ids: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    通过 conditionId 或 tokenIds 查找市场
    
    Args:
        base_url: Gamma API 基础 URL (如果为 None，使用默认值)
        condition_id: 条件 ID
        token_ids: Token ID 列表
    
    Returns:
        市场信息的字典，如果未找到则返回 None
    
    Raises:
        ValueError: 当既没有提供 condition_id 也没有提供 token_ids 时
    """
    if condition_id is None and token_ids is None:
        raise ValueError("Must provide either condition_id or token_ids")
    
    if base_url is None:
        base_url = get_gamma_base_url()
    
    # 如果提供了 condition_id，优先使用它查询
    if condition_id:
        try:
            # 尝试通过 conditionId 查询
            # 注意：Gamma API 可能需要特定的查询格式
            url = f"{base_url}/markets"
            params = {"condition_id": condition_id.lower()}
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                markets = response.json()
                if markets and len(markets) > 0:
                    return markets[0]
        except Exception as e:
            print(f"Error fetching by condition_id: {e}")
    
    # 如果通过 condition_id 没找到，或者只提供了 token_ids，则尝试通过 token_ids 查询
    if token_ids:
        try:
            url = f"{base_url}/markets"
            # 注意：具体的 API 参数可能需要根据实际 API 文档调整
            for token_id in token_ids:
                params = {"token_id": token_id.lower()}
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    markets = response.json()
                    if markets and len(markets) > 0:
                        return markets[0]
        except Exception as e:
            print(f"Error fetching by token_ids: {e}")
    
    return None


def extract_market_params(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 Gamma API 返回的市场数据中提取关键参数
    
    Args:
        market_data: Gamma API 返回的市场数据
    
    Returns:
        包含提取参数的字典，包括：
        - condition_id: 条件 ID
        - question_id: 问题 ID
        - clob_token_ids: CLOB Token IDs 列表 [YES, NO]
        - question: 问题描述
        - end_date_iso: 市场结束时间
        等
    """
    params = {}
    
    # 基本信息
    params['id'] = market_data.get('id', '')
    params['slug'] = market_data.get('slug', '')
    params['question'] = market_data.get('question', '')
    params['description'] = market_data.get('description', '')
    params['end_date_iso'] = market_data.get('endDateIso', market_data.get('end_date_iso', ''))
    
    # 链上参数
    params['condition_id'] = market_data.get('conditionId', market_data.get('condition_id', ''))
    params['question_id'] = market_data.get('questionId', market_data.get('question_id', ''))
    
    # Token IDs - 可能是字符串（JSON）或列表
    clob_token_ids = market_data.get('clobTokenIds', market_data.get('tokenIds', []))
    
    # 如果是字符串，尝试解析 JSON
    if isinstance(clob_token_ids, str):
        try:
            import json
            clob_token_ids = json.loads(clob_token_ids)
        except:
            clob_token_ids = []
    
    # 转换为十六进制格式（如果是十进制数字字符串）
    formatted_token_ids = []
    for token_id in clob_token_ids:
        if isinstance(token_id, str) and token_id.isdigit():
            # 十进制转十六进制
            formatted_token_ids.append(f"0x{int(token_id):064x}")
        elif isinstance(token_id, int):
            formatted_token_ids.append(f"0x{token_id:064x}")
        else:
            formatted_token_ids.append(token_id)
    
    params['clob_token_ids'] = formatted_token_ids
    
    # 通常第一个是 YES，第二个是 NO
    if len(formatted_token_ids) >= 2:
        params['yes_token_id'] = formatted_token_ids[0]
        params['no_token_id'] = formatted_token_ids[1]
    
    # 其他有用信息
    params['market_slug'] = market_data.get('market_slug', params['slug'])
    params['umaBond'] = market_data.get('umaBond', '')
    params['umaReward'] = market_data.get('umaReward', '')
    
    return params


if __name__ == "__main__":
    # 测试示例
    import sys
    
    if len(sys.argv) > 1:
        slug = sys.argv[1]
    else:
        slug = "will-there-be-another-us-government-shutdown-by-january-31"
    
    print(f"Fetching event: {slug}")
    try:
        event = fetch_event_by_slug(None, slug)
        print(f"Event ID: {event.get('id')}")
        print(f"Event Title: {event.get('title')}")
        print(f"Markets count: {len(event.get('markets', []))}")
        
        # 获取第一个市场
        if event.get('markets'):
            first_market = event['markets'][0]
            market_slug = first_market.get('slug', first_market.get('market_slug', ''))
            if market_slug:
                print(f"\nFetching market: {market_slug}")
                market = fetch_market_by_slug(None, market_slug)
                params = extract_market_params(market)
                print(f"Condition ID: {params.get('condition_id')}")
                print(f"Question ID: {params.get('question_id')}")
                print(f"Token IDs: {params.get('clob_token_ids')}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
