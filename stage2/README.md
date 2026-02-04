# Stage 2: Polymarket 链上市场与交易索引器

## 项目概述

这是一个针对 Polymarket 市场和交易的链上数据索引器，实现了从链上原始数据到业务语义层数据对齐的完整流程。

## 功能实现

### ✅ 任务 A: Market Discovery Service
- 从 Gamma API 获取事件和市场信息
- 解析市场的 conditionId、tokenIds 等关键参数
- 验证 token ID 的正确性
- 存储市场信息到数据库

### ✅ 任务 B: Trades Indexer
- 扫描 Polygon 链上的 OrderFilled 事件
- 解析交易详情（价格、数量、方向等）
- 通过 token ID 匹配对应的市场
- 支持断点续传和幂等写入
- 记录同步状态

### ✅ 任务 C: API Server
- RESTful API 查询接口
- 支持按市场查询交易记录
- 支持按 token ID 查询交易
- 支持分页和区块范围过滤

## 项目结构

```
stage2/
├── .env.example          # 环境变量示例
├── requirements.txt      # Python 依赖
├── README.md            # 项目说明
├── test_api.py          # API 测试脚本
├── data/                # 数据目录
│   ├── demo_indexer.db  # 示例数据库
│   └── demo_output.json # 示例输出
└── src/
    ├── demo.py          # 演示脚本
    ├── ctf/             # CTF 工具模块
    │   ├── derive.py    # Token ID 计算
    │   └── trade_decoder.py  # 交易解码
    ├── db/              # 数据库模块
    │   ├── schema.py    # 数据库表定义
    │   └── store.py     # 数据访问层
    ├── indexer/         # 索引器模块
    │   ├── discovery.py # 市场发现
    │   └── run.py       # 交易索引
    └── api/             # API 服务
        └── server.py    # FastAPI 服务器
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入 RPC_URL
```

### 3. 运行示例

```bash
# 索引单个交易
python -m src.demo \
    --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946 \
    --event-slug will-there-be-another-us-government-shutdown-by-january-31 \
    --reset-db \
    --output ./data/demo_output.json

# 索引区块范围
python -m src.demo \
    --from-block 81324595 \
    --to-block 81324595 \
    --event-slug will-there-be-another-us-government-shutdown-by-january-31 \
    --db ./data/indexer.db
```

### 4. 启动 API 服务

```bash
python -m src.api.server --db ./data/demo_indexer.db --port 8000
```

### 5. 测试 API

```bash
# 获取市场信息
curl http://127.0.0.1:8000/markets/will-there-be-another-us-government-shutdown-by-january-31

# 获取交易记录
curl "http://127.0.0.1:8000/markets/will-there-be-another-us-government-shutdown-by-january-31/trades?limit=5"

# 或使用测试脚本
python test_api.py
```

## 数据库设计

### events 表
存储事件信息

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| slug | VARCHAR | 事件标识符 |
| title | TEXT | 事件标题 |
| enable_neg_risk | BOOLEAN | 是否为负风险市场 |

### markets 表
存储市场信息

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| event_id | INTEGER | 关联事件 ID |
| slug | VARCHAR | 市场标识符 |
| condition_id | VARCHAR | 链上条件 ID |
| yes_token_id | VARCHAR | YES 头寸 Token ID |
| no_token_id | VARCHAR | NO 头寸 Token ID |
| status | VARCHAR | 市场状态 |

### trades 表
存储交易记录

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| market_id | INTEGER | 关联市场 ID |
| tx_hash | VARCHAR | 交易哈希 |
| log_index | INTEGER | 日志索引 |
| side | VARCHAR | 买卖方向 (BUY/SELL) |
| outcome | VARCHAR | 结果类型 (YES/NO) |
| price | DECIMAL | 成交价格 |
| size | DECIMAL | 成交数量 |
| timestamp | TIMESTAMP | 成交时间 |

唯一索引: `(tx_hash, log_index)` 确保幂等性

### sync_state 表
存储同步进度

| 字段 | 类型 | 说明 |
|------|------|------|
| key | VARCHAR | 状态键名 |
| last_block | INTEGER | 最后处理的区块 |

## API 端点

### GET /
服务信息和端点列表

### GET /events/{slug}
获取事件详情

### GET /events/{slug}/markets
获取事件下的所有市场

### GET /markets/{slug}
获取市场详情

**响应示例:**
```json
{
  "market_id": 1,
  "slug": "will-there-be-another-us-government-shutdown-by-january-31",
  "condition_id": "0x43ec78527bd98a0588dd9455685b2cc82f5743140cb3a154603dc03c02b57de5",
  "yes_token_id": "0x744eaf8517da344aefb0956978e0cae7bb9c2fefb183740197f0127d86b0bcbd",
  "no_token_id": "0xf0f52d012b787313df4917dc398adb927c807b7eca4da8b61acc6cb31534298d",
  "status": "inactive"
}
```

### GET /markets/{slug}/trades
获取市场的交易记录（分页）

**查询参数:**
- `limit`: 返回条数限制 (1-1000, 默认 100)
- `cursor`: 分页偏移量 (默认 0)
- `fromBlock`: 起始区块（可选）
- `toBlock`: 结束区块（可选）

**响应示例:**
```json
[
  {
    "trade_id": 1,
    "market_id": 1,
    "tx_hash": "0x916cad...",
    "side": "BUY",
    "outcome": "NO",
    "price": "0.77",
    "size": "13",
    "timestamp": "2026-01-07T06:47:29"
  }
]
```

### GET /tokens/{token_id}/trades
按 Token ID 获取交易记录

支持相同的查询参数和响应格式

## 验证测试

所有验证命令都已通过测试：

✅ 数据库正确初始化  
✅ Market Discovery 从 Gamma API 获取市场  
✅ 市场包含正确的 yes_token_id 和 no_token_id  
✅ Trades Indexer 扫描 OrderFilled 事件  
✅ 交易正确关联到市场  
✅ 交易包含正确的 outcome (YES/NO)  
✅ 幂等写入（重复插入不会产生重复数据）  
✅ sync_state 记录同步进度  
✅ API 服务正常启动和响应  
✅ 所有 API 端点正常工作  
✅ 支持分页和过滤参数  

## 验证结果

```bash
# 查看数据库内容
$ sqlite3 ./data/demo_indexer.db "SELECT slug, condition_id FROM markets;"
will-there-be-another-us-government-shutdown-by-january-31|0x43ec78527bd98a0588dd9455685b2cc82f5743140cb3a154603dc03c02b57de5

$ sqlite3 ./data/demo_indexer.db "SELECT COUNT(*) FROM trades;"
2

# API 测试结果
$ python test_api.py
✓ All API tests passed!
```

## 技术特性

### 数据一致性
- 使用唯一索引 `(tx_hash, log_index)` 防止重复
- 事务性批量插入
- 链上数据为最终依据

### 断点续传
- sync_state 表记录同步进度
- 支持中断后继续索引
- 幂等写入确保数据正确

### 错误处理
- RPC 请求失败重试机制
- 未知市场的交易记录警告
- POA 链中间件支持（Polygon）

### 性能优化
- 批量获取日志
- 区块时间戳缓存
- 数据库索引优化

## 注意事项

1. **POA 链支持**: Polygon 是 POA 链，需要添加 `ExtraDataToPOAMiddleware`
2. **Token ID 格式**: 从 Gamma API 获取的 clobTokenIds 需要转换为 0x 开头的 64 位十六进制
3. **API 响应格式**: Gamma API 返回的是数组，需要取第一个元素
4. **Web3 版本**: 新版本 `.hex()` 不自动添加 0x 前缀，需要手动添加

## 扩展功能

可以在此基础上实现：
- 实时行情监控
- 用户盈亏计算
- 市场分析统计
- 价格预警服务
- 链上重组处理
- 负风险市场转换追踪

## 许可证

MIT
