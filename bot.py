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
# 配置：请根据需要修改或改为从环境变量中读取
# ------------------------------------------------------------------------------
URL = "https://recreation.utoronto.ca/booking"

USERNAME = os.environ.get("UTORID")    # 你的 UTORid
PASSWORD = os.environ.get("PASSWORD")  # 密码
SPORT_NAME = "S&R Badminton"         # 要预订的运动名称
BOOKING_TIME = "7 - 7:55 PM"         # 目标时段
CHOSEN_COURT = "Court 01-AC-Badminton"  # 当不遍历所有球场时，指定球场名称
COURT_LOOP = True                    # True=遍历所有球场; False=只预订指定球场
REFRESH_INTERVAL = 10               # 刷新间隔（秒），根据需要调整

CHROMEDRIVER_PATH = ""  # 你的 ChromeDriver 路径
# ------------------------------------------------------------------------------


def setup_driver(chrome_driver_path):
    """
    初始化并返回Chrome WebDriver。
    可在此添加更多启动参数，如禁用通知、隐身模式等。
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-extensions")

    driver = webdriver.Chrome(service=webdriver.chrome.service.Service(chrome_driver_path),
                              options=options)
    return driver


def click_sport(driver, sport_name):
    """
    在体育列表页面点击目标运动卡片。
    若未找到，则抛出异常。
    """
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "container-image-link-item"))
    )

    sports = driver.find_elements(By.CLASS_NAME, "container-image-link-item")
    for sport in sports:
        name = sport.find_element(By.CLASS_NAME, "container-link-text-item").text.strip()
        if name == sport_name:
            sport.find_element(By.TAG_NAME, "a").click()
            print(f"[INFO] 点击了目标运动：'{sport_name}'，等待页面跳转 ...")
            return
    raise Exception(f"[ERROR] 未找到名为 '{sport_name}' 的运动选项。")


def login_with_utorid(driver, username, password):
    """
    点击“使用 UTORID 登录”按钮，并在弹窗中输入用户名、密码进行登录。
    """
    # 点击“使用 UTORID 登录”按钮
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "btn-sso-shibboleth"))
    ).click()
    print("[INFO] 点击了 UTORID 登录按钮，等待登录页面 ...")

    # 输入用户凭据并提交
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "login-btn").click()
    print("[INFO] 已输入UTORid/密码，登录请求已提交。等待重定向 ...")


def select_latest_date(driver):
    """
    在预订页面选择最新可预订的日期。
    如果无法找到日期按钮，则抛出异常。
    """
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "single-date-select-button"))
    )
    days = driver.find_elements(By.CLASS_NAME, "single-date-select-button")
    if not days:
        raise Exception("[ERROR] 未找到可用日期按钮，可能页面结构有变或暂时没有可预订日期。")

    latest_day_button = days[-1]
    day_text = latest_day_button.text.strip()
    latest_day_button.click()
    print(f"[INFO] 已选择最新可用日期：{day_text}")


def is_slot_available(slot):
    """
    判断一个时间槽位是否有可用按钮。
    - 若时段尚未开放（如 "Opens at ..."），或不可用（"No spots available" / "UNAVAILABLE"），则返回 False。
    - 如果有可点击的按钮或显示余位信息，则返回 True。
    """
    text_content = slot.text.strip().upper()
    # 根据页面上可能出现的文案进行判断，可自行扩展逻辑
    # 例如： "UNAVAILABLE", "No spots available", "Opens at X PM", etc.
    if "OPENS AT" in text_content:
        return False
    if "UNAVAILABLE" in text_content:
        return False
    if "NO SPOTS AVAILABLE" in text_content.upper():
        return False
    # 如果都不包含上述关键字，就有可能是可点击的
    return True


def book_time_slot(driver, booking_time, court_loop, chosen_court):
    """
    遍历所有球场（或指定球场）查找目标时段，并尝试点击预订按钮。
    返回 True 表示成功预订，返回 False 表示未成功。
    """
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "tabBookingFacilities"))
    )
    courts = driver.find_elements(By.CSS_SELECTOR, "#tabBookingFacilities button")

    if not courts:
        raise Exception("[ERROR] 页面上未发现任何球场按钮，可能结构变化或加载失败。")

    for court_button in courts:
        court_name = court_button.text.strip()

        if not court_loop and court_name != chosen_court:
            print(f"[INFO] 跳过非目标球场：{court_name}")
            continue

        court_button.click()
        # 让页面有足够时间加载该球场的时段信息
        time.sleep(0.5)

        booking_slots = driver.find_elements(By.CLASS_NAME, "booking-slot-item")
        if not booking_slots:
            print(f"[WARNING] 无法获取 {court_name} 的时段信息，可能页面结构变化。")
            continue

        for slot in booking_slots:
            try:
                slot_text = slot.find_element(By.TAG_NAME, "strong").text.strip()
            except NoSuchElementException:
                # 若 strong 标签结构发生变化，或不存在，则跳过
                continue

            # 匹配用户配置的目标时段
            if slot_text == booking_time:
                print(f"[INFO] 在 '{court_name}' 找到时段：'{booking_time}'。")
                if is_slot_available(slot):
                    # 存在可点击按钮时再尝试查找并点击
                    try:
                        button = slot.find_element(By.TAG_NAME, "button")
                        # 查看按钮是否禁用
                        if "disabled" not in button.get_attribute("class"):
                            print("[INFO] 检测到可预订按钮，开始点击 ...")
                            ActionChains(driver).move_to_element(button).click(button).perform()
                            print(f"[SUCCESS] 已成功预订 '{court_name}' 的 '{booking_time}'。")
                            # 等待一会确保后端处理
                            time.sleep(5)
                            return True
                        else:
                            print(f"[INFO] {booking_time} 在 {court_name} 按钮处于禁用状态。")
                    except NoSuchElementException:
                        print(f"[INFO] '{booking_time}' 时段暂时无可点击按钮，可能未到开放时间。")
                else:
                    print(f"[INFO] '{booking_time}' 时段显示为不可预订或尚未开放。")

                # 找到对应时段后无需再检查该球场的其他时段
                break

        # 如果不循环所有球场，只检查了 chosen_court，就可以中断继续
        if not court_loop:
            break

    return False


def main():
    print("\n===== UofT AC 运动中心预约助手 启动中 / Starting AC Booking Bot =====\n")

    driver = setup_driver(CHROMEDRIVER_PATH)
    try:
        # Step 1: 打开预订页面并点击目标运动
        driver.get(URL)
        click_sport(driver, SPORT_NAME)

        # Step 2: UTORid 登录
        login_with_utorid(driver, USERNAME, PASSWORD)

        # Step 3: 登录完成后，再次点击目标运动（有时页面会跳转回首页，需要再点一次）
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "container-image-link-item"))
        )
        click_sport(driver, SPORT_NAME)

        # Step 4: 循环刷新，寻找可预订时段
        while True:
            try:
                driver.refresh()
                select_latest_date(driver)
                success = book_time_slot(driver, BOOKING_TIME, COURT_LOOP, CHOSEN_COURT)
                if success:
                    print("[INFO] 成功预订后脚本退出。")
                    break
                else:
                    print("[INFO] 暂未找到可预订的时段，或尚未开放，稍后重试 ...")

            except Exception as e:
                print(f"[ERROR] 预订循环中出现异常：{e}")
                print("[INFO] 短暂等待后重试 ...")
                time.sleep(REFRESH_INTERVAL)

    except Exception as e:
        print(f"[FATAL] 遇到严重错误：{e}")

    finally:
        print("\n[INFO] 结束脚本，关闭浏览器。")
        driver.quit()


if __name__ == "__main__":
    main()