import time
import os
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException


# ------------------------------------------------------------------------------
# 配置：可改为从环境变量中读取
# ------------------------------------------------------------------------------
URL = "https://recreation.utoronto.ca/booking"

USERNAME = ""                # 你的 UTORid
PASSWORD = ""            # 密码
SPORT_NAME = "S&R Badminton"         # 要预订的运动名称
BOOKING_TIME = "9 - 9:55 PM"         # 目标时段
CHOSEN_COURT = "Court 01-AC-Badminton"   # 当不遍历所有球场时，指定球场名称
COURT_LOOP = True                    # True=遍历所有球场; False=只预订指定球场
REFRESH_INTERVAL = 0                # 刷新间隔（秒）: 为0则无限快速刷新，谨慎使用！

CHROMEDRIVER_PATH = (
    ""
)  # ChromeDriver 路径
# ------------------------------------------------------------------------------


def setup_driver(chrome_driver_path):
    """
    初始化并返回Chrome WebDriver，配置一些常用选项。
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-extensions")

    driver = webdriver.Chrome(
        service=webdriver.chrome.service.Service(chrome_driver_path),
        options=options
    )
    return driver


def click_sport(driver, sport_name):
    """
    在运动列表页面点击目标运动。
    未找到目标运动时抛出异常。
    """
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "container-image-link-item"))
    )
    sports = driver.find_elements(By.CLASS_NAME, "container-image-link-item")
    for sport in sports:
        name = sport.find_element(By.CLASS_NAME, "container-link-text-item").text.strip()
        if name == sport_name:
            sport.find_element(By.TAG_NAME, "a").click()
            print(f"[INFO] 已点击目标运动：'{sport_name}'")
            return
    raise Exception(f"[ERROR] 未找到名为 '{sport_name}' 的运动选项。")


def login_with_utorid(driver, username, password):
    """
    使用 UTORid 登录。
    """
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "btn-sso-shibboleth"))
    ).click()
    print("[INFO] 点击 '使用 UTORID 登录' 按钮")

    # 输入用户名与密码并登录
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "login-btn").click()
    print("[INFO] 提交登录信息，等待重定向 ...")


def select_latest_date(driver):
    """
    选择最新可预订的日期按钮。
    """
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "single-date-select-button"))
    )
    days = driver.find_elements(By.CLASS_NAME, "single-date-select-button")
    if not days:
        raise Exception("[ERROR] 未找到可用日期按钮，可能页面结构有变。")

    latest_day_button = days[-1]
    day_text = latest_day_button.text.strip()
    latest_day_button.click()
    # 只在第一次或更新选择时打印提示
    print(f"[INFO] 已选择最新可用日期：{day_text}")


def is_slot_available(slot_element):
    """
    判断一个时段槽位是否显示可预订。
    若文本中包含“Opens at”“No spots”或“UNAVAILABLE”等说明不可点击。
    """
    text_content = slot_element.text.strip().upper()
    if "OPENS AT" in text_content:
        return False
    if "UNAVAILABLE" in text_content:
        return False
    if "NO SPOTS AVAILABLE" in text_content:
        return False
    return True


def book_time_slot(driver, booking_time, court_loop, chosen_court):
    """
    遍历所有或指定球场，在找到的目标时段尝试预订。
    成功预订返回 True，否则返回 False。
    """
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "tabBookingFacilities"))
    )
    courts = driver.find_elements(By.CSS_SELECTOR, "#tabBookingFacilities button")
    if not courts:
        raise Exception("[ERROR] 未发现球场按钮，页面可能有变动。")

    booked = False
    for court_button in courts:
        court_name = court_button.text.strip()

        # 如果只想预订特定球场，则跳过其他球场
        if not court_loop and court_name != chosen_court:
            continue

        # 点击球场按钮，加载该球场的时段信息
        court_button.click()
        time.sleep(0.5)  # 等待一点时间，让时段信息加载

        booking_slots = driver.find_elements(By.CLASS_NAME, "booking-slot-item")
        if not booking_slots:
            continue

        for slot in booking_slots:
            # 拿到时段文本
            try:
                slot_text = slot.find_element(By.TAG_NAME, "strong").text.strip()
            except NoSuchElementException:
                continue  # strong 标签不存在就跳过

            # 与用户配置的目标时段匹配
            if slot_text == booking_time:
                if is_slot_available(slot):
                    try:
                        button = slot.find_element(By.TAG_NAME, "button")
                        # 检查按钮是否被禁用
                        if "disabled" not in button.get_attribute("class"):
                            ActionChains(driver).move_to_element(button).click(button).perform()
                            print(f"[SUCCESS] 已成功预订 '{court_name}' 的 '{booking_time}'。")
                            time.sleep(3)  # 等待后端确认
                            booked = True
                            break
                    except NoSuchElementException:
                        # 没有按钮，可能尚未到开放时间
                        pass
                # 一旦匹配了时段，就不再继续检查该球场其他时段
                break

        if booked:
            break  # 不再检查其他球场

    return booked


def main():
    print("\n===== UofT AC 运动中心预约助手 (精简日志版) 启动 =====\n")

    driver = setup_driver(CHROMEDRIVER_PATH)
    try:
        # 1. 打开预约页面并选择运动
        driver.get(URL)
        click_sport(driver, SPORT_NAME)

        # 2. 登录
        login_with_utorid(driver, USERNAME, PASSWORD)

        # 3. 登录后如需再次点击运动选项，则执行
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "container-image-link-item"))
        )
        click_sport(driver, SPORT_NAME)

        # 4. 刷新循环，尝试预订
        attempt_count = 0
        while True:
            attempt_count += 1
            # 打印简单的刷新次数
            print(f"[INFO] 第 {attempt_count} 次检测...")

            driver.refresh()
            select_latest_date(driver)

            if book_time_slot(driver, BOOKING_TIME, COURT_LOOP, CHOSEN_COURT):
                print("[INFO] 预约流程完成，脚本即将退出。")
                break
            else:
                print("[INFO] 暂未找到可预订的时段或尚未开放，等待后重试 ...")

            # 设置刷新间隔(加入随机值可避免固定刷新)
            # time.sleep(REFRESH_INTERVAL + random.uniform(0, 1) if REFRESH_INTERVAL else 1)

    except Exception as e:
        print(f"[FATAL] 运行出现异常：{e}")

    finally:
        print("\n[INFO] 结束脚本，关闭浏览器。")
        driver.quit()


if __name__ == "__main__":
    main()
