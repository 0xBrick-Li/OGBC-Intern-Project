"""
API Server - 任务 C

提供 RESTful API 查询接口。
"""

import argparse
import sqlite3
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn

from src.db.store import (
    fetch_event_by_slug,
    fetch_market_by_slug,
    fetch_markets_by_event_id,
    fetch_trades_for_market,
    fetch_trades_for_token
)


app = FastAPI(title="Polymarket Indexer API", version="1.0.0")

# 全局数据库连接
db_conn: Optional[sqlite3.Connection] = None


def get_db_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    if db_conn is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return db_conn


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "Polymarket Indexer API",
        "version": "1.0.0",
        "endpoints": [
            "/events/{slug}",
            "/events/{slug}/markets",
            "/markets/{slug}",
            "/markets/{slug}/trades",
            "/tokens/{token_id}/trades"
        ]
    }


@app.get("/events/{slug}")
async def get_event(slug: str):
    """
    获取事件详情
    
    Args:
        slug: 事件 slug
        
    Returns:
        事件信息
    """
    conn = get_db_connection()
    event = fetch_event_by_slug(conn, slug)
    
    if not event:
        raise HTTPException(status_code=404, detail=f"Event not found: {slug}")
    
    return event


@app.get("/events/{slug}/markets")
async def get_event_markets(slug: str):
    """
    获取事件下的所有市场
    
    Args:
        slug: 事件 slug
        
    Returns:
        市场列表
    """
    conn = get_db_connection()
    
    # 先获取事件
    event = fetch_event_by_slug(conn, slug)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event not found: {slug}")
    
    # 获取市场列表
    markets = fetch_markets_by_event_id(conn, event['id'])
    
    return {
        "event_slug": slug,
        "event_id": event['id'],
        "total_markets": len(markets),
        "markets": markets
    }


@app.get("/markets/{slug}")
async def get_market(slug: str):
    """
    获取市场详情
    
    Args:
        slug: 市场 slug
        
    Returns:
        市场信息
    """
    conn = get_db_connection()
    market = fetch_market_by_slug(conn, slug)
    
    if not market:
        raise HTTPException(status_code=404, detail=f"Market not found: {slug}")
    
    return market


@app.get("/markets/{slug}/trades")
async def get_market_trades(
    slug: str,
    limit: int = Query(default=100, ge=1, le=1000),
    cursor: int = Query(default=0, ge=0),
    fromBlock: Optional[int] = Query(default=None, ge=0),
    toBlock: Optional[int] = Query(default=None, ge=0)
):
    """
    获取市场的交易记录（分页）
    
    Args:
        slug: 市场 slug
        limit: 返回条数限制 (1-1000)
        cursor: 分页偏移量
        fromBlock: 起始区块（可选）
        toBlock: 结束区块（可选）
        
    Returns:
        交易记录列表
    """
    conn = get_db_connection()
    
    # 先获取市场
    market = fetch_market_by_slug(conn, slug)
    if not market:
        raise HTTPException(status_code=404, detail=f"Market not found: {slug}")
    
    # 获取交易记录
    trades = fetch_trades_for_market(
        conn=conn,
        market_id=market['market_id'],
        limit=limit,
        cursor=cursor,
        from_block=fromBlock,
        to_block=toBlock
    )
    
    return trades


@app.get("/tokens/{token_id}/trades")
async def get_token_trades(
    token_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    cursor: int = Query(default=0, ge=0),
    fromBlock: Optional[int] = Query(default=None, ge=0),
    toBlock: Optional[int] = Query(default=None, ge=0)
):
    """
    按 TokenId 获取交易记录（分页）
    
    Args:
        token_id: Token ID
        limit: 返回条数限制 (1-1000)
        cursor: 分页偏移量
        fromBlock: 起始区块（可选）
        toBlock: 结束区块（可选）
        
    Returns:
        交易记录列表
    """
    conn = get_db_connection()
    
    # 获取交易记录
    trades = fetch_trades_for_token(
        conn=conn,
        token_id=token_id,
        limit=limit,
        cursor=cursor,
        from_block=fromBlock,
        to_block=toBlock
    )
    
    return trades


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


def start_server(
    db_path: str,
    host: str = "127.0.0.1",
    port: int = 8000
):
    """
    启动 API 服务器
    
    Args:
        db_path: 数据库文件路径
        host: 监听地址
        port: 监听端口
    """
    global db_conn
    
    # 初始化数据库连接
    db_conn = sqlite3.connect(db_path, check_same_thread=False)
    
    print(f"Starting API server on {host}:{port}")
    print(f"Database: {db_path}")
    
    # 启动服务器
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Polymarket Indexer API Server")
    parser.add_argument("--db", required=True, help="Database file path")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    
    args = parser.parse_args()
    
    start_server(db_path=args.db, host=args.host, port=args.port)
