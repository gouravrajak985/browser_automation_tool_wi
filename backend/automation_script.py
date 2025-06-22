from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import pickle
import os
from datetime import datetime

# Global driver instance for manual login
manual_login_driver = None

def run_automation(cookie_name, start_row, end_row):
    """Main automation function with detailed logging"""
    try:
        # Load data
        data = pd.read_csv("Pending E-kyc.csv")
        data.columns = [col.strip().lower() for col in data.columns]
        
        # Set row range
        range_df = data.iloc[start_row:end_row].copy()
        
        if "memberid" not in range_df.columns or "familyid" not in range_df.columns:
            raise ValueError("Missing 'memberid' or 'familyid' column")
        
        # Group members by FamilyID
        family_groups = range_df.groupby('familyid')['memberid'].apply(list).to_dict()
        print(f"🔍 Found {len(family_groups)} families with members.")
        
        # Prepare task list
        tasks = []
        for fam_id, members in family_groups.items():
            for i in range(len(members)):
                duplicate = confirm = str(members[i])
                if i < len(members) - 1:
                    original = str(members[i + 1])
                elif i > 0:
                    original = str(members[i - 1])
                else:
                    continue
                tasks.append((duplicate, confirm, original, fam_id))
        
        # Setup Chrome
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 15)
        
        try:
            # Load cookies
            driver.get("https://spr.samagra.gov.in/Login/Public/sLogin.aspx")
            cookie_path = f"cookies/{cookie_name}.pkl"
            
            if os.path.exists(cookie_path):
                with open(cookie_path, "rb") as f:
                    for cookie in pickle.load(f):
                        driver.add_cookie(cookie)
                print("✅ Cookies loaded.")
            else:
                raise Exception("Cookie file not found")
            
            # Process tasks
            success_log = []
            fail_log = []
            
            for idx, (dup, conf, orig, fam) in enumerate(tasks):
                try:
                    print(f"\n🔄 [{idx+1}/{len(tasks)}] Processing FamilyID={fam}, Duplicate={dup}, Original={orig}")
                    
                    # Navigate to removal page
                    driver.get("https://spr.samagra.gov.in/MemberMgmt/Pages/Remove_Member.aspx")
                    time.sleep(1)
                    
                    # Fill duplicate member ID
                    dup_field = wait.until(EC.presence_of_element_located((By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtDupSamagraId")))
                    dup_field.clear()
                    dup_field.send_keys(dup)
                    time.sleep(1)
                    print(f"✓ Entered duplicate member ID: {dup}")
                    
                    # Fill confirm member ID
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtConfirmSamagraId").clear()
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtConfirmSamagraId").send_keys(conf)
                    time.sleep(1)
                    print(f"✓ Entered confirm member ID: {conf}")
                    
                    # Fill original member ID
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtOriSamagraId").clear()
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtOriSamagraId").send_keys(orig)
                    time.sleep(1)
                    print(f"✓ Entered original member ID: {orig}")
                    
                    # Click show button
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_BtnShow").click()
                    time.sleep(2)
                    print("✓ Clicked show button, verifying member details...")
                    
                    # Confirm original member ID
                    wait.until(EC.presence_of_element_located((By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtConfirlOriSamagraId"))).send_keys(orig)
                    time.sleep(1)
                    print(f"✓ Confirmed original member ID: {orig}")
                    
                    # Add removal remark
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtRemoveRemark").send_keys("Duplicate member removal - automated process")
                    time.sleep(1)
                    print("✓ Added removal remark")
                    
                    # Check confirmation checkbox
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_chkconfirm").click()
                    print("✓ Confirmed removal checkbox")
                    
                    # Click delete button
                    wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_btnDelete"))).click()
                    time.sleep(2)
                    
                    print(f"✅ Member {dup} removed successfully from Family {fam}")
                    success_log.append({
                        "familyid": fam, 
                        "memberid": dup, 
                        "status": "Removed",
                        "timestamp": datetime.now().isoformat(),
                        "original_member": orig
                    })
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"⚠️ Failed to remove member {dup} from Family {fam}: {error_msg}")
                    fail_log.append({
                        "familyid": fam, 
                        "memberid": dup, 
                        "status": "Failed", 
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat(),
                        "original_member": orig
                    })
                    continue
                
                # Progress update
                progress = ((idx + 1) / len(tasks)) * 100
                print(f"📊 Progress: {progress:.1f}% ({idx+1}/{len(tasks)})")
                
                time.sleep(1)
            
            # Save logs with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            success_filename = f"logs/success_removed_{cookie_name}_{start_row}_{end_row}_{timestamp}.csv"
            fail_filename = f"logs/failed_removal_{cookie_name}_{start_row}_{end_row}_{timestamp}.csv"
            
            # Save detailed logs
            if success_log:
                pd.DataFrame(success_log).to_csv(success_filename, index=False)
                print(f"✅ Success log saved: {success_filename}")
            
            if fail_log:
                pd.DataFrame(fail_log).to_csv(fail_filename, index=False)
                print(f"⚠️ Failure log saved: {fail_filename}")
            
            # Also save latest logs for quick access
            pd.DataFrame(success_log).to_csv("logs/success_removed_latest.csv", index=False)
            pd.DataFrame(fail_log).to_csv("logs/failed_removal_latest.csv", index=False)
            
            result = {
                'success_count': len(success_log),
                'fail_count': len(fail_log),
                'success_file': success_filename if success_log else None,
                'fail_file': fail_filename if fail_log else None,
                'total_processed': len(tasks)
            }
            
            print(f"\n🎉 Automation completed!")
            print(f"📊 Total processed: {len(tasks)}")
            print(f"✅ Successful: {len(success_log)}")
            print(f"⚠️ Failed: {len(fail_log)}")
            
            return result
            
        finally:
            driver.quit()
            print("🔒 Browser session closed")
            
    except Exception as e:
        print(f"❌ Automation failed: {e}")
        raise e

def start_manual_login(cookie_name):
    """Start browser for manual login"""
    global manual_login_driver
    
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    
    manual_login_driver = webdriver.Chrome(options=options)
    manual_login_driver.get("https://spr.samagra.gov.in/Login/Public/sLogin.aspx")
    
    print(f"🔐 Browser opened for manual login. Session will be saved as: {cookie_name}")
    return True

def save_cookies_and_run(cookie_name, start_row, end_row):
    """Save cookies from manual login and run automation"""
    global manual_login_driver
    
    if manual_login_driver is None:
        raise Exception("No manual login session found")
    
    try:
        # Save cookies
        cookie_path = f"cookies/{cookie_name}.pkl"
        with open(cookie_path, "wb") as f:
            pickle.dump(manual_login_driver.get_cookies(), f)
        
        print(f"✅ Session cookies saved as {cookie_path}")
        
        # Close manual login browser
        manual_login_driver.quit()
        manual_login_driver = None
        
        # Run automation
        return run_automation(cookie_name, start_row, end_row)
        
    except Exception as e:
        if manual_login_driver:
            manual_login_driver.quit()
            manual_login_driver = None
        raise e