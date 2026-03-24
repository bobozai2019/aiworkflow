"""测试 Agent 权限配置"""
from pathlib import Path
from src.core.permission import get_permission_manager, Permission

pm = get_permission_manager()
pm.initialize(Path('.'))

print('=' * 60)
print('Agent 权限配置检查')
print('=' * 60)

agents = ['需求分析师', '系统架构师', '代码开发者', '测试员']

for agent in agents:
    print(f'\n【{agent}】')
    perm = pm.get_permission(agent)
    if perm:
        for dp in perm.directories:
            p = dp.permission
            p_str = '读写' if p == Permission.READ_WRITE else ('只读' if p == Permission.READ else ('只写' if p == Permission.WRITE else '无权限'))
            print(f'  {dp.directory}: {p_str}')

print('\n' + '=' * 60)
print('权限测试')
print('=' * 60)

test_cases = [
    ('需求分析师', 'requirements/test.md', 'write', True),
    ('需求分析师', 'code/test.py', 'read', False),
    ('系统架构师', 'requirements/test.md', 'read', True),
    ('系统架构师', 'code/architecture.md', 'write', True),
    ('系统架构师', 'tests/test.py', 'write', False),
    ('代码开发者', 'requirements/test.md', 'read', True),
    ('代码开发者', 'code/main.py', 'write', True),
    ('代码开发者', 'tests/test.py', 'write', False),
    ('测试员', '.', 'read', True),
    ('测试员', 'requirements/test.md', 'read', True),
    ('测试员', 'code/main.py', 'read', True),
    ('测试员', 'tests/test_main.py', 'write', True),
    ('测试员', 'code/test.py', 'write', False),
]

all_pass = True
for agent, path, mode, expected in test_cases:
    if mode == 'read':
        result = pm.check_read_permission(agent, Path(path))
    else:
        result = pm.check_write_permission(agent, Path(path))
    status = '✅' if result == expected else '❌'
    if result != expected:
        all_pass = False
    print(f'{status} {agent} {mode} {path} (预期: {expected}, 实际: {result})')

print('\n' + '=' * 60)
if all_pass:
    print('✅ 所有权限测试通过！')
else:
    print('❌ 部分权限测试失败！')
print('=' * 60)
