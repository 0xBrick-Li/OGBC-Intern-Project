"""
CTF Token ID Derivation

根据 Gnosis Conditional Token Framework 计算市场头寸的 Token ID。
"""

from dataclasses import dataclass
from typing import Optional
from web3 import Web3
from eth_abi import encode


@dataclass(frozen=True)
class BinaryPositions:
    """二元市场的两个头寸 Token ID"""
    position_yes: str  # YES Token ID (hex string)
    position_no: str   # NO Token ID (hex string)
    collection_yes: str  # YES Collection ID (hex string)
    collection_no: str   # NO Collection ID (hex string)


def get_collection_id(
    parent_collection_id: str,
    condition_id: str,
    index_set: int
) -> str:
    """
    计算 Collection ID
    
    collectionId = keccak256(parentCollectionId, conditionId, indexSet)
    
    Args:
        parent_collection_id: 父集合 ID (hex string, 0x + 64 chars)
        condition_id: 条件 ID (hex string, 0x + 64 chars)
        index_set: 索引集合 (1 for YES, 2 for NO)
    
    Returns:
        Collection ID (hex string, 0x + 64 chars)
    """
    # 确保输入格式正确
    if not parent_collection_id.startswith('0x'):
        parent_collection_id = '0x' + parent_collection_id
    if not condition_id.startswith('0x'):
        condition_id = '0x' + condition_id
    
    # 将 hex string 转为 bytes32
    parent_bytes = bytes.fromhex(parent_collection_id[2:].zfill(64))
    condition_bytes = bytes.fromhex(condition_id[2:].zfill(64))
    
    # 编码参数并计算哈希
    # abi.encodePacked(bytes32, bytes32, uint256)
    packed = parent_bytes + condition_bytes + index_set.to_bytes(32, 'big')
    collection_id = Web3.keccak(packed)
    
    return '0x' + collection_id.hex()


def get_position_id(
    collateral_token: str,
    collection_id: str
) -> str:
    """
    计算 Position ID (Token ID)
    
    positionId = keccak256(collateralToken, collectionId)
    
    Args:
        collateral_token: 抵押品代币地址 (hex string)
        collection_id: 集合 ID (hex string)
    
    Returns:
        Position ID (hex string, 0x + 64 chars)
    """
    # 确保地址格式正确
    if not collateral_token.startswith('0x'):
        collateral_token = '0x' + collateral_token
    if not collection_id.startswith('0x'):
        collection_id = '0x' + collection_id
    
    # 将地址转为 bytes20，collection_id 转为 bytes32
    token_bytes = bytes.fromhex(collateral_token[2:].zfill(40))
    collection_bytes = bytes.fromhex(collection_id[2:].zfill(64))
    
    # abi.encodePacked(address, bytes32)
    # address is 20 bytes, bytes32 is 32 bytes
    packed = token_bytes + collection_bytes
    position_id = Web3.keccak(packed)
    
    return '0x' + position_id.hex()


def get_condition_id(
    oracle: str,
    question_id: str,
    outcome_slot_count: int
) -> str:
    """
    计算 Condition ID
    
    conditionId = keccak256(oracle, questionId, outcomeSlotCount)
    
    Args:
        oracle: 预言机地址 (hex string)
        question_id: 问题 ID (hex string)
        outcome_slot_count: 结果槽数量 (通常为 2)
    
    Returns:
        Condition ID (hex string, 0x + 64 chars)
    """
    # 确保格式正确
    if not oracle.startswith('0x'):
        oracle = '0x' + oracle
    if not question_id.startswith('0x'):
        question_id = '0x' + question_id
    
    # 使用 eth_abi 编码参数
    # abi.encode(address, bytes32, uint256)
    encoded = encode(
        ['address', 'bytes32', 'uint256'],
        [
            Web3.to_checksum_address(oracle),
            bytes.fromhex(question_id[2:].zfill(64)),
            outcome_slot_count
        ]
    )
    
    condition_id = Web3.keccak(encoded)
    return '0x' + condition_id.hex()


def derive_binary_positions(
    oracle: str,
    question_id: str,
    collateral_token: str,
    condition_id: Optional[str] = None,
    parent_collection_id: str = "0x0000000000000000000000000000000000000000000000000000000000000000"
) -> BinaryPositions:
    """
    为二元市场计算 YES 和 NO 两个头寸的 Token ID
    
    Args:
        oracle: 预言机地址 (hex string)
        question_id: 问题 ID (hex string)
        collateral_token: 抵押品代币地址 (hex string)
        condition_id: 条件 ID (可选，如果不提供会根据参数计算)
        parent_collection_id: 父集合 ID (默认为 0x0...0)
    
    Returns:
        BinaryPositions 对象，包含 YES/NO 的 Token ID 和 Collection ID
    """
    # 如果没有提供 condition_id，则计算它
    if condition_id is None:
        condition_id = get_condition_id(oracle, question_id, 2)
    
    # 计算 YES 和 NO 的 Collection ID
    # YES: indexSet = 1 (0b01)
    # NO: indexSet = 2 (0b10)
    collection_yes = get_collection_id(parent_collection_id, condition_id, 1)
    collection_no = get_collection_id(parent_collection_id, condition_id, 2)
    
    # 计算 YES 和 NO 的 Position ID (Token ID)
    position_yes = get_position_id(collateral_token, collection_yes)
    position_no = get_position_id(collateral_token, collection_no)
    
    return BinaryPositions(
        position_yes=position_yes,
        position_no=position_no,
        collection_yes=collection_yes,
        collection_no=collection_no
    )


def normalize_hex(value: str) -> str:
    """
    规范化十六进制字符串格式
    
    Args:
        value: 十六进制字符串
    
    Returns:
        规范化后的字符串 (0x + lowercase hex)
    """
    if not value:
        return value
    
    if value.startswith('0x'):
        return '0x' + value[2:].lower()
    else:
        return '0x' + value.lower()


if __name__ == "__main__":
    # 测试示例
    # Polymarket USDC.e 地址 (Polygon)
    USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    
    # 示例参数
    oracle = "0x157Ce2d672854c848c9b79C49a8Cc6cc89176a49"
    question_id = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    
    # 计算 positions
    positions = derive_binary_positions(
        oracle=oracle,
        question_id=question_id,
        collateral_token=USDC_ADDRESS
    )
    
    print("Binary Position Derivation Test:")
    print(f"YES Token ID: {positions.position_yes}")
    print(f"NO Token ID:  {positions.position_no}")
    print(f"YES Collection ID: {positions.collection_yes}")
    print(f"NO Collection ID:  {positions.collection_no}")
