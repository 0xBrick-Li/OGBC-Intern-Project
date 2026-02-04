"""
数据存储访问层

提供数据库 CRUD 操作函数。
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple


def upsert_event(conn: sqlite3.Connection, event: Dict[str, Any]) -> int:
    """
    插入或更新事件信息
    
    Args:
        conn: 数据库连接
        event: 事件信息字典
        
    Returns:
        事件 ID
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO events (slug, title, description, start_date, end_date, enable_neg_risk, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(slug) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            start_date = excluded.start_date,
            end_date = excluded.end_date,
            enable_neg_risk = excluded.enable_neg_risk,
            updated_at = CURRENT_TIMESTAMP
    """, (
        event.get('slug'),
        event.get('title'),
        event.get('description'),
        event.get('start_date'),
        event.get('end_date'),
        event.get('enable_neg_risk', False)
    ))
    
    # 获取插入或更新的事件 ID
    cursor.execute("SELECT id FROM events WHERE slug = ?", (event.get('slug'),))
    result = cursor.fetchone()
    conn.commit()
    
    return result[0] if result else None


def upsert_market(conn: sqlite3.Connection, market: Dict[str, Any]) -> int:
    """
    插入或更新市场信息
    
    Args:
        conn: 数据库连接
        market: 市场信息字典
        
    Returns:
        市场 ID
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO markets (
            event_id, slug, condition_id, question_id, oracle, 
            collateral_token, yes_token_id, no_token_id, 
            enable_neg_risk, status, title, description, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(condition_id) DO UPDATE SET
            event_id = excluded.event_id,
            slug = excluded.slug,
            question_id = excluded.question_id,
            oracle = excluded.oracle,
            collateral_token = excluded.collateral_token,
            yes_token_id = excluded.yes_token_id,
            no_token_id = excluded.no_token_id,
            enable_neg_risk = excluded.enable_neg_risk,
            status = excluded.status,
            title = excluded.title,
            description = excluded.description,
            updated_at = CURRENT_TIMESTAMP
    """, (
        market.get('event_id'),
        market.get('slug'),
        market.get('condition_id'),
        market.get('question_id'),
        market.get('oracle'),
        market.get('collateral_token'),
        market.get('yes_token_id'),
        market.get('no_token_id'),
        market.get('enable_neg_risk', False),
        market.get('status', 'active'),
        market.get('title'),
        market.get('description')
    ))
    
    # 获取插入或更新的市场 ID
    cursor.execute("SELECT id FROM markets WHERE condition_id = ?", (market.get('condition_id'),))
    result = cursor.fetchone()
    conn.commit()
    
    return result[0] if result else None


def insert_trades(conn: sqlite3.Connection, trades: List[Dict[str, Any]]) -> int:
    """
    批量插入交易记录（忽略重复）
    
    Args:
        conn: 数据库连接
        trades: 交易记录列表
        
    Returns:
        成功插入的记录数
    """
    if not trades:
        return 0
    
    cursor = conn.cursor()
    inserted_count = 0
    
    for trade in trades:
        try:
            cursor.execute("""
                INSERT INTO trades (
                    market_id, tx_hash, log_index, block_number, timestamp,
                    exchange, order_hash, maker, taker, side, outcome,
                    price, size, token_id, maker_asset_id, taker_asset_id,
                    maker_amount, taker_amount, fee
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.get('market_id'),
                trade.get('tx_hash'),
                trade.get('log_index'),
                trade.get('block_number'),
                trade.get('timestamp'),
                trade.get('exchange'),
                trade.get('order_hash'),
                trade.get('maker'),
                trade.get('taker'),
                trade.get('side'),
                trade.get('outcome'),
                trade.get('price'),
                trade.get('size'),
                trade.get('token_id'),
                trade.get('maker_asset_id'),
                trade.get('taker_asset_id'),
                trade.get('maker_amount'),
                trade.get('taker_amount'),
                trade.get('fee')
            ))
            inserted_count += 1
        except sqlite3.IntegrityError:
            # 忽略重复记录
            pass
    
    conn.commit()
    return inserted_count


def update_sync_state(conn: sqlite3.Connection, key: str, last_block: int) -> None:
    """
    更新同步状态
    
    Args:
        conn: 数据库连接
        key: 状态键
        last_block: 最后处理的区块高度
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sync_state (key, last_block, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            last_block = excluded.last_block,
            updated_at = CURRENT_TIMESTAMP
    """, (key, last_block))
    conn.commit()


def get_sync_state(conn: sqlite3.Connection, key: str) -> Optional[int]:
    """
    获取同步状态
    
    Args:
        conn: 数据库连接
        key: 状态键
        
    Returns:
        最后处理的区块高度，如果不存在则返回 None
    """
    cursor = conn.cursor()
    cursor.execute("SELECT last_block FROM sync_state WHERE key = ?", (key,))
    result = cursor.fetchone()
    return result[0] if result else None


def fetch_event_by_slug(conn: sqlite3.Connection, slug: str) -> Optional[Dict[str, Any]]:
    """
    根据 slug 查询事件
    
    Args:
        conn: 数据库连接
        slug: 事件 slug
        
    Returns:
        事件信息字典，如果不存在则返回 None
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, slug, title, description, start_date, end_date, 
               enable_neg_risk, created_at, updated_at
        FROM events WHERE slug = ?
    """, (slug,))
    
    result = cursor.fetchone()
    if not result:
        return None
    
    return {
        'id': result[0],
        'slug': result[1],
        'title': result[2],
        'description': result[3],
        'start_date': result[4],
        'end_date': result[5],
        'enable_neg_risk': bool(result[6]),
        'created_at': result[7],
        'updated_at': result[8]
    }


def fetch_market_by_slug(conn: sqlite3.Connection, slug: str) -> Optional[Dict[str, Any]]:
    """
    根据 slug 查询市场
    
    Args:
        conn: 数据库连接
        slug: 市场 slug
        
    Returns:
        市场信息字典，如果不存在则返回 None
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, event_id, slug, condition_id, question_id, oracle,
               collateral_token, yes_token_id, no_token_id, enable_neg_risk,
               status, title, description, created_at, updated_at
        FROM markets WHERE slug = ?
    """, (slug,))
    
    result = cursor.fetchone()
    if not result:
        return None
    
    return {
        'market_id': result[0],
        'event_id': result[1],
        'slug': result[2],
        'condition_id': result[3],
        'question_id': result[4],
        'oracle': result[5],
        'collateral_token': result[6],
        'yes_token_id': result[7],
        'no_token_id': result[8],
        'enable_neg_risk': bool(result[9]),
        'status': result[10],
        'title': result[11],
        'description': result[12],
        'created_at': result[13],
        'updated_at': result[14]
    }


def fetch_market_by_token_id(conn: sqlite3.Connection, token_id: str) -> Optional[Dict[str, Any]]:
    """
    根据 token_id 查询市场
    
    Args:
        conn: 数据库连接
        token_id: Token ID (yes 或 no)
        
    Returns:
        市场信息字典，如果不存在则返回 None
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, event_id, slug, condition_id, question_id, oracle,
               collateral_token, yes_token_id, no_token_id, enable_neg_risk,
               status, title, description, created_at, updated_at
        FROM markets WHERE yes_token_id = ? OR no_token_id = ?
    """, (token_id, token_id))
    
    result = cursor.fetchone()
    if not result:
        return None
    
    return {
        'market_id': result[0],
        'event_id': result[1],
        'slug': result[2],
        'condition_id': result[3],
        'question_id': result[4],
        'oracle': result[5],
        'collateral_token': result[6],
        'yes_token_id': result[7],
        'no_token_id': result[8],
        'enable_neg_risk': bool(result[9]),
        'status': result[10],
        'title': result[11],
        'description': result[12],
        'created_at': result[13],
        'updated_at': result[14]
    }


def fetch_markets_by_event_id(conn: sqlite3.Connection, event_id: int) -> List[Dict[str, Any]]:
    """
    根据事件 ID 查询所有市场
    
    Args:
        conn: 数据库连接
        event_id: 事件 ID
        
    Returns:
        市场信息列表
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, event_id, slug, condition_id, question_id, oracle,
               collateral_token, yes_token_id, no_token_id, enable_neg_risk,
               status, title, description, created_at, updated_at
        FROM markets WHERE event_id = ?
        ORDER BY created_at DESC
    """, (event_id,))
    
    results = cursor.fetchall()
    markets = []
    for result in results:
        markets.append({
            'market_id': result[0],
            'event_id': result[1],
            'slug': result[2],
            'condition_id': result[3],
            'question_id': result[4],
            'oracle': result[5],
            'collateral_token': result[6],
            'yes_token_id': result[7],
            'no_token_id': result[8],
            'enable_neg_risk': bool(result[9]),
            'status': result[10],
            'title': result[11],
            'description': result[12],
            'created_at': result[13],
            'updated_at': result[14]
        })
    
    return markets


def fetch_trades_for_market(
    conn: sqlite3.Connection,
    market_id: int,
    limit: int = 100,
    cursor: int = 0,
    from_block: Optional[int] = None,
    to_block: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    查询市场的交易记录
    
    Args:
        conn: 数据库连接
        market_id: 市场 ID
        limit: 返回条数限制
        cursor: 分页偏移量
        from_block: 起始区块
        to_block: 结束区块
        
    Returns:
        交易记录列表
    """
    db_cursor = conn.cursor()
    
    # 构建查询条件
    where_clauses = ["market_id = ?"]
    params = [market_id]
    
    if from_block is not None:
        where_clauses.append("block_number >= ?")
        params.append(from_block)
    
    if to_block is not None:
        where_clauses.append("block_number <= ?")
        params.append(to_block)
    
    where_clause = " AND ".join(where_clauses)
    
    # 添加分页参数
    params.extend([limit, cursor])
    
    db_cursor.execute(f"""
        SELECT id, market_id, tx_hash, log_index, block_number, timestamp,
               exchange, order_hash, maker, taker, side, outcome,
               price, size, token_id, maker_asset_id, taker_asset_id,
               maker_amount, taker_amount, fee, created_at
        FROM trades
        WHERE {where_clause}
        ORDER BY block_number ASC, log_index ASC
        LIMIT ? OFFSET ?
    """, params)
    
    results = db_cursor.fetchall()
    trades = []
    for result in results:
        trades.append({
            'trade_id': result[0],
            'market_id': result[1],
            'tx_hash': result[2],
            'log_index': result[3],
            'block_number': result[4],
            'timestamp': result[5],
            'exchange': result[6],
            'order_hash': result[7],
            'maker': result[8],
            'taker': result[9],
            'side': result[10],
            'outcome': result[11],
            'price': result[12],
            'size': result[13],
            'token_id': result[14],
            'maker_asset_id': result[15],
            'taker_asset_id': result[16],
            'maker_amount': result[17],
            'taker_amount': result[18],
            'fee': result[19],
            'created_at': result[20]
        })
    
    return trades


def fetch_trades_for_token(
    conn: sqlite3.Connection,
    token_id: str,
    limit: int = 100,
    cursor: int = 0,
    from_block: Optional[int] = None,
    to_block: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    查询指定 token_id 的交易记录
    
    Args:
        conn: 数据库连接
        token_id: Token ID
        limit: 返回条数限制
        cursor: 分页偏移量
        from_block: 起始区块
        to_block: 结束区块
        
    Returns:
        交易记录列表
    """
    db_cursor = conn.cursor()
    
    # 构建查询条件
    where_clauses = ["token_id = ?"]
    params = [token_id]
    
    if from_block is not None:
        where_clauses.append("block_number >= ?")
        params.append(from_block)
    
    if to_block is not None:
        where_clauses.append("block_number <= ?")
        params.append(to_block)
    
    where_clause = " AND ".join(where_clauses)
    
    # 添加分页参数
    params.extend([limit, cursor])
    
    db_cursor.execute(f"""
        SELECT id, market_id, tx_hash, log_index, block_number, timestamp,
               exchange, order_hash, maker, taker, side, outcome,
               price, size, token_id, maker_asset_id, taker_asset_id,
               maker_amount, taker_amount, fee, created_at
        FROM trades
        WHERE {where_clause}
        ORDER BY block_number ASC, log_index ASC
        LIMIT ? OFFSET ?
    """, params)
    
    results = db_cursor.fetchall()
    trades = []
    for result in results:
        trades.append({
            'trade_id': result[0],
            'market_id': result[1],
            'tx_hash': result[2],
            'log_index': result[3],
            'block_number': result[4],
            'timestamp': result[5],
            'exchange': result[6],
            'order_hash': result[7],
            'maker': result[8],
            'taker': result[9],
            'side': result[10],
            'outcome': result[11],
            'price': result[12],
            'size': result[13],
            'token_id': result[14],
            'maker_asset_id': result[15],
            'taker_asset_id': result[16],
            'maker_amount': result[17],
            'taker_amount': result[18],
            'fee': result[19],
            'created_at': result[20]
        })
    
    return trades
