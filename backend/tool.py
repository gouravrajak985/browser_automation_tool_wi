from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import pickle
import os

# Load data
data = pd.read_csv("Pending E-kyc.csv")
data.columns = [col.strip().lower() for col in data.columns]

# Set row range
start_row = 9404
end_row = 9470
range_df = data.iloc[start_row:end_row].copy()

if "memberid" not in range_df.columns or "familyid" not in range_df.columns:
    raise ValueError("Missing 'memberid' or 'familyid' column")

# Group members by FamilyID
family_groups = range_df.groupby('familyid')['memberid'].apply(list).to_dict()
print(f"🔍 Found {len(family_groups)} families with members.")

# Prepare task list: list of (duplicate, confirm, original)
tasks = []
for fam_id, members in family_groups.items():
    for i in range(len(members)):
        duplicate = confirm = str(members[i])
        if i < len(members) - 1:
            original = str(members[i + 1])
        elif i > 0:
            original = str(members[i - 1])
        else:
            continue  # Skip if only one member in family
        tasks.append((duplicate, confirm, original, fam_id))
        print(f"🔍 Task added for FamilyID={fam_id}: Duplicate={duplicate}, Original={original}")

# Setup Chrome
options = Options()
options.add_argument(r"--user-data-dir=C:\Temp\SeleniumProfile")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

# Cookie logic
driver.get("https://spr.samagra.gov.in/Login/Public/sLogin.aspx")
if os.path.exists("cookies_gourav.pkl"):
    with open("cookies_gourav.pkl", "rb") as f:
        for cookie in pickle.load(f):
            driver.add_cookie(cookie)

    print("✅ Cookies loaded.")
else:
    input("🔐 Login manually and press ENTER...")
    with open("cookies_gourav.pkl", "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    print("✅ Cookies saved. Re-run script.")
    driver.quit()
    exit()

# Logs
success_log = []
fail_log = []

# Process each task
for dup, conf, orig, fam in tasks:
    try:
        print(f"\n🔄 Processing FamilyID={fam}, Duplicate={dup}, Original={orig}")
        driver.get("https://spr.samagra.gov.in/MemberMgmt/Pages/Remove_Member.aspx")
        time.sleep(1)  # Wait for page to load
        dup_field = wait.until(EC.presence_of_element_located((By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtDupSamagraId")))
        dup_field.clear()
        dup_field.send_keys(dup)
        time.sleep(1)  # Wait for input to be processed
        print("🔍 Searching for duplicate member...")
        driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtConfirmSamagraId").clear()
        driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtConfirmSamagraId").send_keys(conf)
        time.sleep(1)  # Wait for input to be processed
        print("🔍 Searching for confirmed member...")
        driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtOriSamagraId").clear()
        driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtOriSamagraId").send_keys(orig)
        time.sleep(1)  # Wait for input to be processed
        print("🔍 Searching for original member...")
        driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_BtnShow").click()
        time.sleep(2)
        print("🔍 Checking if member exists...")

        # Confirm original
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtConfirlOriSamagraId"))).send_keys(orig)
        time.sleep(1)  # Wait for input to be processed
        print("🔍 Confirming original member...")
        driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtRemoveRemark").send_keys("okay")
        time.sleep(1)  # Wait for input to be processed
        print("🔍 Removing member...")
        driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_chkconfirm").click()
        wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_btnDelete"))).click()
        time.sleep(1)  # Wait for removal to process
        print("✅ Member removed successfully.")
        success_log.append({"familyid": fam, "memberid": dup, "status": "Removed"})
        

    except Exception as e:
        print(f"⚠️ Failed: {e}")
        fail_log.append({"familyid": fam, "memberid": dup, "status": "Failed", "error": str(e)})
        continue

    time.sleep(1)  # Wait before next task


# Save logs
# Dynamic filenames
success_filename = f"success_removed_{start_row+2}_{end_row}.csv"
fail_filename = f"failed_removal_{start_row+2}_{end_row}.csv"

# Save logs with dynamic names
pd.DataFrame(success_log).to_csv(success_filename, index=False)
pd.DataFrame(fail_log).to_csv(fail_filename, index=False)

print("\n✅ All done.")
driver.quit()
    