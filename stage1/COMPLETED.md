# Stage 1 任务完成说明

## 已完成内容

✅ **任务 A：交易解码器 (Trade Decoder)**
- 实现了完整的交易日志解析功能
- 支持解析 `OrderFilled` 事件
- 正确计算价格、判断买卖方向
- 过滤重复日志（taker == exchange）

✅ **任务 B：市场解码器 (Market Decoder)**
- 实现了 CTF Token ID 计算工具
- 支持从 Gamma API 获取市场信息
- 支持从链上交易解析 `ConditionPreparation` 事件
- 验证计算结果与 Gamma API 数据的一致性

✅ **综合演示脚本**
- 整合交易解析和市场解码功能
- 自动匹配交易与市场
- 输出完整的分析结果

## 项目结构

```
stage1/
├── src/
│   ├── __init__.py
│   ├── trade_decoder.py      # 任务 A: 交易解码器
│   ├── market_decoder.py     # 任务 B: 市场解码器
│   ├── demo.py               # 综合演示
│   ├── ctf/
│   │   ├── __init__.py
│   │   └── derive.py         # CTF Token ID 计算
│   └── indexer/
│       ├── __init__.py
│       └── gamma.py          # Gamma API 客户端
├── data/                     # 输出数据目录
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量示例
├── .env                      # 环境变量配置（需用户配置）
├── verify.sh                 # 验证脚本
├── README.md                 # 项目说明
└── stage1.md                 # 任务文档
```

## 使用前准备

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 RPC URL

**重要**: 需要配置有效的 Polygon RPC URL 才能运行交易解码功能。

步骤：
1. 访问 [Alchemy](https://www.alchemy.com/) 或 [Infura](https://www.infura.io/)
2. 注册并创建一个 Polygon Mainnet 项目
3. 复制 RPC URL
4. 编辑 `.env` 文件：

```bash
# 编辑 .env 文件
nano .env

# 或使用你喜欢的编辑器
code .env
```

将 `YOUR_API_KEY` 替换为你的实际 API 密钥：

```env
RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/你的实际API密钥
```

### 3. 测试 CTF Token ID 计算（无需 RPC）

可以先测试 Token ID 计算功能，这不需要 RPC 连接：

```bash
python -m src.ctf.derive
```

预期输出：
```
Binary Position Derivation Test:
YES Token ID: 0xee2a564d105b2be970b7791e0b84e94c6632c4c3371a664d341a681b98fe9e9c
NO Token ID:  0xa5c1382b57c66763bef217e29014da0e5c50f1592ffe6652c2e29e06ae3757fc
...
```

## 运行验证

### 方法 1: 使用验证脚本（推荐）

配置好 RPC URL 后，运行：

```bash
./verify.sh
```

这将依次测试：
1. 交易解码器
2. 市场解码器
3. 综合演示

### 方法 2: 手动运行各个模块

#### 任务 A: 交易解码器

```bash
# 基础用法
python -m src.trade_decoder \
    --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946

# 输出到文件
python -m src.trade_decoder \
    --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946 \
    --output ./data/trades.json
```

#### 任务 B: 市场解码器

```bash
# 注意：示例文档中的 market slug 可能已过期
# 你需要使用当前有效的市场 slug

# 通过 Gamma API
python -m src.market_decoder \
    --market-slug <有效的市场slug>

# 通过交易哈希（如果有 ConditionPreparation 事件）
python -m src.market_decoder \
    --tx-hash <交易哈希> \
    --log-index <日志索引>
```

#### 综合演示

```bash
python -m src.demo \
    --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946 \
    --event-slug <有效的市场slug> \
    --output ./data/demo_output.json
```

## 实现细节

### 交易解码器 (trade_decoder.py)

核心功能：
- 解析 `OrderFilled` 事件的所有字段
- 根据 `makerAssetId` 判断交易方向（0 = BUY, 非0 = SELL）
- 计算成交价格：`price = USDC_amount / token_amount`
- 过滤掉 `taker == exchange` 的重复日志

关键数据结构：
```python
@dataclass
class Trade:
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
    side: str  # "BUY" or "SELL"
```

### 市场解码器 (market_decoder.py)

核心功能：
- 从 Gamma API 获取市场元数据
- 计算 YES/NO Token ID
- 验证计算结果与 API 数据的一致性
- 支持从链上 `ConditionPreparation` 事件解析

Token ID 计算过程：
1. `collectionId_yes = keccak256(0x0, conditionId, 1)`
2. `collectionId_no = keccak256(0x0, conditionId, 2)`
3. `yesTokenId = keccak256(USDC_address, collectionId_yes)`
4. `noTokenId = keccak256(USDC_address, collectionId_no)`

### CTF Token ID 计算 (ctf/derive.py)

实现了 Gnosis Conditional Token Framework 的 Token ID 计算算法：
- `get_condition_id()`: 计算 Condition ID
- `get_collection_id()`: 计算 Collection ID
- `get_position_id()`: 计算 Position ID (Token ID)
- `derive_binary_positions()`: 一站式计算二元市场的 YES/NO Token ID

### Gamma API 客户端 (indexer/gamma.py)

提供与 Polymarket Gamma API 交互的功能：
- `fetch_event_by_slug()`: 获取事件信息
- `fetch_market_by_slug()`: 获取市场信息
- `extract_market_params()`: 提取关键参数

## 验证清单

- [x] CTF Token ID 计算功能正常
- [ ] 交易解码器能正确解析 `OrderFilled` 事件（需要 RPC URL）
- [ ] 交易解码器正确计算价格和方向（需要 RPC URL）
- [ ] 市场解码器能从 Gamma API 获取市场信息（需要有效的 market slug）
- [ ] 市场解码器能正确计算 Token ID
- [ ] 计算的 Token ID 与 Gamma API 返回的一致
- [ ] 综合演示能整合两个任务（需要 RPC URL 和有效的 market slug）

## 已知问题和注意事项

1. **Market Slug 时效性**: 文档中的示例 market slug `will-there-be-another-us-government-shutdown-by-january-31` 可能已过期。使用时需要找到当前有效的市场 slug。

2. **RPC URL 必需**: 交易解码功能需要有效的 Polygon RPC URL。建议使用：
   - Alchemy: https://www.alchemy.com/
   - Infura: https://www.infura.io/
   - 公共 RPC（可能不稳定）: https://polygon-rpc.com/

3. **API 速率限制**: Gamma API 和 RPC 提供商都可能有速率限制，频繁请求可能被限流。

## 下一步

完成验证后，可以：
1. 使用自己感兴趣的交易哈希进行测试
2. 探索更多 Polymarket 市场
3. 分析不同市场的交易模式
4. 为 Stage 2 做准备

## 技术栈

- **Web3.py**: 与 Polygon 链交互
- **eth-abi**: ABI 编码/解码
- **requests**: HTTP 请求
- **python-dotenv**: 环境变量管理

## 贡献者

本项目完成了 Polymarket 链上数据解析的基础功能，为后续的索引器开发奠定了基础。
