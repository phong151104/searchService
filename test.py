import json

# Đọc file
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# In ra phần data
print(data.get('data', []))

# Lấy phần trong "data"
entries = data["data"]

# Ví dụ: in ra từng câu hỏi
for entry in entries:
    print(entry["question"])
