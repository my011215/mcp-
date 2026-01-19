import json

# 简洁版本
with open('system.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 提取所有 content
contents = []
for i, message in enumerate(data['messages']):
    content = message.get('content')
    if content:
        contents.append(content)
        print(f"Message {i} ({message['role']}):")
        # print(content)
        print()

# 写入 Markdown 文件
with open('prompt-system.md', 'w', encoding='utf-8') as f:
    # f.write("# 提取的系统提示词\n\n")
    # f.write(f"## 提示词 {i}\n\n")
    f.write(str(contents[0]))
    f.write("\n\n---\n\n")

print(f"✅ 已将 {len(contents)} 条提示词保存到 prompt-system.md")