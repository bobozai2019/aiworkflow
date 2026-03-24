"""
权限控制功能测试脚本
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.permission import (
    Permission,
    DirectoryPermission,
    AgentPermission,
    PermissionManager,
    get_permission_manager,
)


def test_permission_enum():
    """测试权限枚举"""
    print("\n=== 测试权限枚举 ===")
    
    assert Permission.NONE.can_read() == False
    assert Permission.NONE.can_write() == False
    
    assert Permission.READ.can_read() == True
    assert Permission.READ.can_write() == False
    
    assert Permission.WRITE.can_read() == False
    assert Permission.WRITE.can_write() == True
    
    assert Permission.READ_WRITE.can_read() == True
    assert Permission.READ_WRITE.can_write() == True
    
    print("✓ 权限枚举测试通过")


def test_directory_permission():
    """测试目录权限"""
    print("\n=== 测试目录权限 ===")
    
    project_root = Path("D:/test_project")
    
    dir_perm = DirectoryPermission(
        directory="requirements",
        permission=Permission.READ_WRITE,
        description="需求文档目录"
    )
    
    file_path = project_root / "requirements" / "test.md"
    assert dir_perm.matches(file_path, project_root) == True
    
    other_path = project_root / "code" / "test.py"
    assert dir_perm.matches(other_path, project_root) == False
    
    print("✓ 目录权限测试通过")


def test_agent_permission():
    """测试Agent权限"""
    print("\n=== 测试Agent权限 ===")
    
    project_root = Path("D:/test_project")
    
    agent_perm = AgentPermission(
        agent_name="测试Agent",
        directories=[
            DirectoryPermission("requirements", Permission.READ_WRITE),
            DirectoryPermission("code", Permission.READ),
        ]
    )
    
    req_file = project_root / "requirements" / "test.md"
    assert agent_perm.get_permission_for_path(req_file, project_root) == Permission.READ_WRITE
    
    code_file = project_root / "code" / "main.py"
    assert agent_perm.get_permission_for_path(code_file, project_root) == Permission.READ
    
    other_file = project_root / "other" / "file.txt"
    assert agent_perm.get_permission_for_path(other_file, project_root) == Permission.NONE
    
    print("✓ Agent权限测试通过")


def test_permission_manager():
    """测试权限管理器"""
    print("\n=== 测试权限管理器 ===")
    
    pm = get_permission_manager()
    project_root = Path("D:/test_project")
    pm.initialize(project_root)
    
    print("\n需求分析师权限:")
    info = pm.get_permission_info("需求分析师")
    print(f"  目录: {info['directories']}")
    
    print("\n系统架构师权限:")
    info = pm.get_permission_info("系统架构师")
    print(f"  目录: {info['directories']}")
    
    print("\n代码开发者权限:")
    info = pm.get_permission_info("代码开发者")
    print(f"  目录: {info['directories']}")
    
    print("\n测试员权限:")
    info = pm.get_permission_info("测试员")
    print(f"  目录: {info['directories']}")
    
    req_file = project_root / "requirements" / "test.md"
    code_file = project_root / "code" / "main.py"
    tests_file = project_root / "tests" / "test_main.py"
    
    print("\n权限检查测试:")
    
    # 需求分析师: 只能访问 requirements/
    assert pm.check_read_permission("需求分析师", req_file) == True
    assert pm.check_write_permission("需求分析师", req_file) == True
    assert pm.check_read_permission("需求分析师", code_file) == False
    assert pm.check_read_permission("需求分析师", tests_file) == False
    print("  ✓ 需求分析师权限正确 (仅 requirements/ 读写)")
    
    # 系统架构师: 可读 requirements/, 可读写 code/
    assert pm.check_read_permission("系统架构师", req_file) == True
    assert pm.check_write_permission("系统架构师", req_file) == False
    assert pm.check_read_permission("系统架构师", code_file) == True
    assert pm.check_write_permission("系统架构师", code_file) == True
    assert pm.check_read_permission("系统架构师", tests_file) == False
    print("  ✓ 系统架构师权限正确 (requirements/ 只读, code/ 读写)")
    
    # 代码开发者: 可读 requirements/, 可读写 code/
    assert pm.check_read_permission("代码开发者", req_file) == True
    assert pm.check_write_permission("代码开发者", req_file) == False
    assert pm.check_read_permission("代码开发者", code_file) == True
    assert pm.check_write_permission("代码开发者", code_file) == True
    assert pm.check_read_permission("代码开发者", tests_file) == False
    print("  ✓ 代码开发者权限正确 (requirements/ 只读, code/ 读写)")
    
    # 测试员: 可读 requirements/ 和 code/, 可读写 tests/
    assert pm.check_read_permission("测试员", req_file) == True
    assert pm.check_write_permission("测试员", req_file) == False
    assert pm.check_read_permission("测试员", code_file) == True
    assert pm.check_write_permission("测试员", code_file) == False
    assert pm.check_read_permission("测试员", tests_file) == True
    assert pm.check_write_permission("测试员", tests_file) == True
    print("  ✓ 测试员权限正确 (requirements/ 只读, code/ 只读, tests/ 读写)")
    
    print("\n✓ 权限管理器测试通过")


def main():
    """运行所有测试"""
    print("=" * 50)
    print("权限控制功能测试")
    print("=" * 50)
    
    try:
        test_permission_enum()
        test_directory_permission()
        test_agent_permission()
        test_permission_manager()
        
        print("\n" + "=" * 50)
        print("所有测试通过! ✓")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
