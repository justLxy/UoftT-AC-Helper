from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Configuration
URL = "https://recreation.utoronto.ca/booking"
USERNAME = ""  # Replace with your UTORid
PASSWORD = ""  # Replace with your password
BOOKING_TIME = "7:45 - 8:30 PM"  # Replace with desired time
SPORT_NAME = "S&R American Squash Crts"  # Sport to book
REFRESH_INTERVAL = 0  # Time (in seconds) between page refreshes
CHROMEDRIVER_PATH = "chromedriver.exe"

# Initialize WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-extensions")
driver = webdriver.Chrome(service=webdriver.chrome.service.Service(CHROMEDRIVER_PATH), options=options)

try:
	# Step 1: Open the booking page and click the link for the desired sport
	driver.get(URL)
	WebDriverWait(driver, 10).until(
		EC.presence_of_all_elements_located((By.CLASS_NAME, "container-image-link-item"))
	)

	sports = driver.find_elements(By.CLASS_NAME, "container-image-link-item")
	sport_clicked = False

	for sport in sports:
		sport_name = sport.find_element(By.CLASS_NAME, "container-link-text-item").text.strip()
		if sport_name == SPORT_NAME:
			sport.find_element(By.TAG_NAME, "a").click()
			# print(f"Clicked on '{SPORT_NAME}'. Waiting for login popup...")
			sport_clicked = True
			break

	if not sport_clicked:
		raise Exception(f"Sport '{SPORT_NAME}' not found on the page.")

	# Step 2: Click the "Log in with UTORID" button
	WebDriverWait(driver, 10).until(
		EC.element_to_be_clickable((By.CLASS_NAME, "btn-sso-shibboleth"))
	).click()
	# print("Clicked UTORID login button, waiting for login page...")

	# Step 3: Enter UTORid and password, and log in
	WebDriverWait(driver, 10).until(
		EC.presence_of_element_located((By.ID, "username"))
	)
	driver.find_element(By.ID, "username").send_keys(USERNAME)
	driver.find_element(By.ID, "password").send_keys(PASSWORD)
	driver.find_element(By.ID, "login-btn").click()
	# print("Login submitted, waiting to return to booking page...")

	# Step 4: Wait until redirected back to the booking page and click the sport again
	WebDriverWait(driver, 15).until(
		EC.presence_of_element_located((By.CLASS_NAME, "container-image-link-item"))
	)

	sports = driver.find_elements(By.CLASS_NAME, "container-image-link-item")
	sport_clicked = False

	for sport in sports:
		sport_name = sport.find_element(By.CLASS_NAME, "container-link-text-item").text.strip()
		if sport_name == SPORT_NAME:
			sport.find_element(By.TAG_NAME, "a").click()
			# print(f"Clicked on '{SPORT_NAME}' again. Now on booking page.")
			sport_clicked = True
			break

	if not sport_clicked:
		raise Exception(f"Sport '{SPORT_NAME}' not found on the page after login.")

	# Booking loop
	while True:
		try:
			# Refresh the page
			driver.refresh()

			# Step 5: Select the latest available day
			WebDriverWait(driver, 10).until(
				EC.presence_of_all_elements_located((By.CLASS_NAME, "single-date-select-button"))
			)
			days = driver.find_elements(By.CLASS_NAME, "single-date-select-button")
			latest_day_button = days[-1]  # Select the last button
			latest_day_button.click()
			# print("Selected the latest available day.")

			# Step 6: Iterate through all courts and book the desired time slot
			WebDriverWait(driver, 10).until(
				EC.presence_of_element_located((By.ID, "tabBookingFacilities"))
			)
			courts = driver.find_elements(By.CSS_SELECTOR, "#tabBookingFacilities button")


			for court in courts:
				court_name = court.text.strip()
				# print(f"Checking slots for {court_name}...")
				court.click()
				time.sleep(1)  # Allow time for the page to update

				# Check booking slots for the selected court
				booking_slots = driver.find_elements(By.CLASS_NAME, "booking-slot-item")
				for slot in booking_slots:
					slot_text = slot.find_element(By.TAG_NAME, "p").text.strip()  # Extract time
					if slot_text == BOOKING_TIME:
						# Check if the booking is available and not disabled or future
						try:
							button = slot.find_element(By.TAG_NAME, "button")
							if "disabled" not in button.get_attribute("class"):
								# print(f"Booking available for {BOOKING_TIME} on {court_name}. Attempting to book...")
								ActionChains(driver).move_to_element(button).click(button).perform()
								print("Booking successful!")
								time.sleep(10)
								exit()
							else:
								# print(f"{BOOKING_TIME} is unavailable on {court_name}.")
								pass
						except Exception as e:
							# print(f"Skipping slot '{slot_text}' on {court_name}: {e}")
							pass
						break

				# Check for "Opens at" text
				if any("Opens at" in slot.text for slot in booking_slots):
					# print(f"Slots for {court_name} haven't opened yet.")
					pass

			# print("Finished checking all courts. Retrying in a few seconds...")
			time.sleep(REFRESH_INTERVAL)

		except Exception as e:
			# print(f"Error during booking process: {e}")
			time.sleep(REFRESH_INTERVAL)

except Exception as e:
	print(f"An error occurred: {e}")

finally:
	driver.quit()
