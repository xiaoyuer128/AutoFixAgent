import os
import sys
from dotenv import load_dotenv
import dashscope
from dashscope import Generation

print("="*50)
print("千问API配置检测工具")
print("="*50)

# 1. 检查.env文件路径
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
print(f"1. 检查.env文件路径: {env_path}")
if not os.path.exists(env_path):
    print("❌ 错误：项目根目录下未找到.env文件！")
    print("   请在项目根目录创建.env文件，添加：DASHSCOPE_API_KEY=你的API密钥")
    sys.exit(1)
print("✅ .env文件存在")

# 2. 加载并读取API密钥
load_dotenv(env_path)
api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
model_name = os.getenv("QWEN_MODEL_NAME", "qwen-plus")

print(f"2. 读取API密钥: {api_key[:5]}...{api_key[-5:] if len(api_key) > 10 else '无'}")
if not api_key:
    print("❌ 错误：DASHSCOPE_API_KEY未配置！")
    print("   请在.env文件中添加：DASHSCOPE_API_KEY=你的阿里云通义千问API密钥")
    sys.exit(1)
print("✅ API密钥已配置")

# 3. 配置dashscope
dashscope.api_key = api_key
base_url = os.getenv("DASHSCOPE_BASE_URL", "")
if base_url:
    dashscope.base_url = base_url
    print(f"3. 使用自定义Base URL: {base_url}")

print(f"4. 使用模型: {model_name}")
print("5. 正在测试API调用...")

# 4. 测试API调用
try:
    response = Generation.call(
        model=model_name,
        messages=[{"role": "user", "content": "你好，请回复一句话证明你可用。"}],
        temperature=0.1,
        max_tokens=100,
        timeout=10
    )
    
    if response.status_code == 200:
        print(f"✅ API调用成功！")
        print(f"   模型返回: {response.output.text.strip()}")
        print("\n🎉 千问配置完全正常，可以使用大模型修复功能！")
    else:
        print(f"❌ API调用失败！")
        print(f"   状态码: {response.status_code}")
        print(f"   错误信息: {response.message}")
        if response.status_code == 401:
            print("\n💡 401错误解决方案：")
            print("   1. 检查API密钥是否正确，不要有多余空格")
            print("   2. 确认密钥是否还在有效期内，没有欠费")
            print("   3. 确认开通了通义千问API服务")
        elif response.status_code == 404:
            print("\n💡 404错误解决方案：")
            print("   1. 检查模型名称是否正确，可尝试改为 qwen-turbo / qwen-plus / qwen-max")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ 调用异常: {str(e)}")
    print("\n💡 可能的原因：")
    print("   1. 网络无法访问阿里云API，请检查网络连接")
    print("   2. dashscope库版本过低，执行 pip install --upgrade dashscope")
    sys.exit(1)

print("="*50)
