import os
import json
import requests
import time
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 配置文件路径
config_file_path = "config.json"
签到结果 = ""

# 获取html中的用户信息
def fetch_and_extract_info(domain, headers):
    url = f"{domain}/user"

    # 发起 GET 请求
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("用户信息获取失败，页面打开异常.")
        return None

    # 解析网页内容
    soup = BeautifulSoup(response.text, 'html.parser')

    # 找到所有 script 标签
    script_tags = soup.find_all('script')

    # 提取 ChatraIntegration 的 script 内容
    chatra_script = None
    for script in script_tags:
        if 'window.ChatraIntegration' in str(script):
            chatra_script = script.string
            break

    if not chatra_script:
        print("未识别到用户信息")
        return None

    # 使用正则表达式提取需要的信息
    user_info = {}
    user_info['到期时间'] = re.search(r"'Class_Expire': '(.*?)'", chatra_script).group(1) if re.search(r"'Class_Expire': '(.*?)'", chatra_script) else None
    user_info['剩余流量'] = re.search(r"'Unused_Traffic': '(.*?)'", chatra_script).group(1) if re.search(r"'Unused_Traffic': '(.*?)'", chatra_script) else None

    用户信息 = f"到期时间: {user_info['到期时间']}\n剩余流量: {user_info['剩余流量']}\n"
    return 用户信息

def generate_config():
    # 获取环境变量
    domain = os.getenv('DOMAIN', 'https://69yun69.com')  # 默认值，如果未设置环境变量
    email_user = os.getenv('EMAIL_USER')  # 邮箱账号
    email_password = os.getenv('EMAIL_PASSWORD')  # 邮箱密码
    recipients = os.getenv('EMAIL_RECIPIENTS', '').split(',')  # 收件人列表，用逗号分隔

    # 获取用户和密码的环境变量
    accounts = []
    index = 1

    while True:
        user = os.getenv(f'USER{index}')
        password = os.getenv(f'PASS{index}')

        if not user or not password:
            break  # 如果没有找到更多的用户信息，则退出循环

        accounts.append({
            'user': user,
            'pass': password
        })
        index += 1

    # 构造配置数据
    config = {
        'domain': domain,
        'email_user': email_user,
        'email_password': email_password,
        'email_recipients': recipients,
        'accounts': accounts
    }
    return config

# 发送电子邮件的函数
def send_email(subject, body, email_user, email_password, recipients):
    # 设置邮件的内容
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        # 连接到SMTP服务器并发送邮件
        server = smtplib.SMTP('smtp.gmail.com', 587)  # 使用 Gmail SMTP 服务器，端口587
        server.starttls()  # 启动 TLS 加密
        server.login(email_user, email_password)  # 登录SMTP服务器
        text = msg.as_string()
        server.sendmail(email_user, recipients, text)  # 发送邮件
        server.quit()
        print(f"邮件已发送给: {', '.join(recipients)}")
    except Exception as e:
        print(f"发送邮件时发生错误: {str(e)}")

# 登录并签到的主要函数
def checkin(account, domain, email_user, email_password, recipients):
    user = account['user']
    pass_ = account['pass']

    签到结果 = f"地址: {domain[:9]}****{domain[-5:]}\n账号: {user[:1]}****{user[-5:]}\n密码: {pass_[:1]}****{pass_[-1]}\n\n"

    try:
        # 检查必要的配置参数是否存在
        if not domain or not user or not pass_:
            raise ValueError('必需的配置参数缺失')

        # 登录请求的 URL
        login_url = f"{domain}/auth/login"

        # 登录请求的 Payload（请求体）
        login_data = {
            'email': user,
            'passwd': pass_,
            'remember_me': 'on',
            'code': "",
        }

        # 设置请求头
        login_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': domain,
            'Referer': f"{domain}/auth/login",
        }

        # 发送登录请求
        login_response = requests.post(login_url, json=login_data, headers=login_headers)

        print(f'{user}账号登录状态:', login_response.status_code)

        # 如果响应状态不是200，表示登录失败
        if login_response.status_code != 200:
            raise ValueError(f"登录请求失败: {login_response.text}")

        # 解析登录响应的 JSON 数据
        login_json = login_response.json()

        # 检查登录是否成功
        if login_json.get("ret") != 1:
            raise ValueError(f"登录失败: {login_json.get('msg', '未知错误')}")

        # 获取登录成功后的 Cookie
        cookies = login_response.cookies
        if not cookies:
            raise ValueError('登录成功但未收到Cookie')

        # 等待确保登录状态生效
        time.sleep(1)

        # 签到请求的 URL
        checkin_url = f"{domain}/user/checkin"

        # 签到请求的 Headers
        checkin_headers = {
            'Cookie': '; '.join([f"{key}={value}" for key, value in cookies.items()]),
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Origin': domain,
            'Referer': f"{domain}/user/panel",
            'X-Requested-With': 'XMLHttpRequest'
        }

        # 发送签到请求
        checkin_response = requests.post(checkin_url, headers=checkin_headers)

        print(f'{user}账号签到状态:', checkin_response.status_code)

        # 获取签到请求的响应内容
        response_text = checkin_response.text

        try:
            # 尝试解析签到的 JSON 响应
            checkin_result = checkin_response.json()
            账号信息 = f"地址: {domain}\n账号: {user}\n密码: <tg-spoiler>{pass_}</tg-spoiler>\n"

            用户信息 = fetch_and_extract_info(domain, checkin_headers)

            # 根据返回的结果更新签到信息
            if checkin_result.get('ret') == 1 or checkin_result.get('ret') == 0:
                签到结果 = f"🎉 签到结果 🎉\n {checkin_result.get('msg', '签到成功' if checkin_result['ret'] == 1 else '签到失败')}"
            else:
                签到结果 = f"🎉 签到结果 🎉\n {checkin_result.get('msg', '签到结果未知')}"
        except Exception as e:
            # 如果出现解析错误，检查是否由于登录失效
            if "登录" in response_text:
                raise ValueError('登录状态无效，请检查Cookie处理')
            raise ValueError(f"解析签到响应失败: {str(e)}\n\n原始响应: {response_text}")

        # 发送签到结果到邮箱
        subject = f"签到结果: {user}"
        body = 账号信息 + 用户信息 + 签到结果
        send_email(subject, body, email_user, email_password, recipients)

        return 签到结果

    except Exception as error:
        # 捕获异常，打印错误并发送错误信息到邮箱
        print(f'{user}账号签到异常:', error)
        签到结果 = f"签到过程发生错误: {error}"
        send_email("签到失败", 签到结果, email_user, email_password, recipients)
        return 签到结果

# 主程序执行逻辑
if __name__ == "__main__":
    # 读取配置
    config = generate_config()

    # 读取全局配置
    domain = config['domain']
    email_user = config['email_user']
    email_password = config['email_password']
    recipients = config['email_recipients']

    # 循环执行每个账号的签到任务
    for account in config.get("accounts", []):
        print("----------------------------------签到信息----------------------------------")
        print(checkin(account, domain, email_user, email_password, recipients))
        print("---------------------------------------------------------------------------")
