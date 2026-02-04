"""
数据库 Schema 定义

定义 Polymarket 索引器所需的数据库表结构。
"""

import sqlite3
from pathlib import Path
from typing import Optional


def init_db(db_path: str) -> sqlite3.Connection:
    """
    初始化数据库，创建所有必要的表
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        数据库连接对象
    """
    # 确保目录存在
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.Connection(db_path)
    cursor = conn.cursor()
    
    # 创建 events 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug VARCHAR(255) UNIQUE NOT NULL,
            title TEXT,
            description TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            enable_neg_risk BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建 markets 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS markets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            slug VARCHAR(255) UNIQUE NOT NULL,
            condition_id VARCHAR(66) UNIQUE NOT NULL,
            question_id VARCHAR(66) NOT NULL,
            oracle VARCHAR(42) NOT NULL,
            collateral_token VARCHAR(42) NOT NULL,
            yes_token_id VARCHAR(78) NOT NULL,
            no_token_id VARCHAR(78) NOT NULL,
            enable_neg_risk BOOLEAN DEFAULT 0,
            status VARCHAR(50) DEFAULT 'active',
            title TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)
    
    # 为 markets 表创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_markets_condition_id 
        ON markets(condition_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_markets_yes_token_id 
        ON markets(yes_token_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_markets_no_token_id 
        ON markets(no_token_id)
    """)
    
    # 创建 trades 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id INTEGER NOT NULL,
            tx_hash VARCHAR(66) NOT NULL,
            log_index INTEGER NOT NULL,
            block_number INTEGER NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            exchange VARCHAR(42) NOT NULL,
            order_hash VARCHAR(66) NOT NULL,
            maker VARCHAR(42) NOT NULL,
            taker VARCHAR(42) NOT NULL,
            side VARCHAR(10) NOT NULL,
            outcome VARCHAR(10) NOT NULL,
            price VARCHAR(50) NOT NULL,
            size VARCHAR(50) NOT NULL,
            token_id VARCHAR(78) NOT NULL,
            maker_asset_id VARCHAR(78) NOT NULL,
            taker_asset_id VARCHAR(78) NOT NULL,
            maker_amount VARCHAR(50) NOT NULL,
            taker_amount VARCHAR(50) NOT NULL,
            fee VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tx_hash, log_index),
            FOREIGN KEY (market_id) REFERENCES markets(id)
        )
    """)
    
    # 为 trades 表创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_market_id 
        ON trades(market_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_block_number 
        ON trades(block_number)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_timestamp 
        ON trades(timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_token_id 
        ON trades(token_id)
    """)
    
    # 创建 sync_state 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_state (
            key VARCHAR(50) PRIMARY KEY,
            last_block INTEGER NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    return conn


def reset_db(db_path: str) -> sqlite3.Connection:
    """
    重置数据库，删除所有表并重新创建
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        数据库连接对象
    """
    # 删除数据库文件
    db_file = Path(db_path)
    if db_file.exists():
        db_file.unlink()
    
    # 重新初始化
    return init_db(db_path)


if __name__ == "__main__":
    # 测试数据库初始化
    conn = init_db("./data/test.db")
    print("数据库初始化成功！")
    
    # 验证表是否创建
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"创建的表: {[t[0] for t in tables]}")
    
    conn.close()
