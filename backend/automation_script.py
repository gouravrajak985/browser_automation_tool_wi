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

# Global variable to store running tasks for progress updates
running_tasks = {}

def update_task_progress(task_id, progress, current_member=None, current_family=None, step_message=None):
    """Update task progress with detailed step information"""
    if task_id in running_tasks:
        running_tasks[task_id]['progress'] = progress
        if current_member:
            running_tasks[task_id]['current_member'] = current_member
        if current_family:
            running_tasks[task_id]['current_family'] = current_family
        if step_message:
            if 'console_logs' not in running_tasks[task_id]:
                running_tasks[task_id]['console_logs'] = []
            running_tasks[task_id]['console_logs'].append(step_message)
            print(f"📝 {step_message}")

def run_automation(cookie_name, start_row, end_row, task_id=None):
    """Main automation function with detailed logging"""
    try:
        update_task_progress(task_id, 5, step_message="🔍 Loading CSV data file...")
        
        # Load data
        data = pd.read_csv("Pending E-kyc.csv")
        data.columns = [col.strip().lower() for col in data.columns]
        
        update_task_progress(task_id, 10, step_message=f"✅ CSV loaded successfully. Total rows: {len(data)}")
        
        # Set row range
        range_df = data.iloc[start_row:end_row].copy()
        
        if "memberid" not in range_df.columns or "familyid" not in range_df.columns:
            raise ValueError("Missing 'memberid' or 'familyid' column")
        
        update_task_progress(task_id, 15, step_message=f"📊 Processing rows {start_row} to {end_row} ({len(range_df)} records)")
        
        # Group members by FamilyID
        family_groups = range_df.groupby('familyid')['memberid'].apply(list).to_dict()
        update_task_progress(task_id, 20, step_message=f"🔍 Found {len(family_groups)} families with members")
        
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
        
        update_task_progress(task_id, 25, step_message=f"📋 Generated {len(tasks)} automation tasks")
        
        # Setup Chrome
        update_task_progress(task_id, 30, step_message="🌐 Initializing Chrome browser...")
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 15)
        
        try:
            # Load cookies
            update_task_progress(task_id, 35, step_message="🔐 Loading authentication session...")
            driver.get("https://spr.samagra.gov.in/Login/Public/sLogin.aspx")
            cookie_path = f"cookies/{cookie_name}.pkl"
            
            if os.path.exists(cookie_path):
                with open(cookie_path, "rb") as f:
                    for cookie in pickle.load(f):
                        driver.add_cookie(cookie)
                update_task_progress(task_id, 40, step_message="✅ Authentication session loaded successfully")
            else:
                raise Exception("Cookie file not found")
            
            # Process tasks
            success_log = []
            fail_log = []
            
            update_task_progress(task_id, 45, step_message="🚀 Starting member removal automation...")
            
            for idx, (dup, conf, orig, fam) in enumerate(tasks):
                try:
                    base_progress = 45 + (idx / len(tasks)) * 50  # Progress from 45% to 95%
                    
                    update_task_progress(task_id, base_progress, current_member=dup, current_family=fam, 
                                       step_message=f"🔄 [{idx+1}/{len(tasks)}] Starting task for Family {fam}")
                    
                    # Navigate to removal page
                    update_task_progress(task_id, base_progress + 1, 
                                       step_message=f"🌐 Navigating to member removal page...")
                    driver.get("https://spr.samagra.gov.in/MemberMgmt/Pages/Remove_Member.aspx")
                    time.sleep(1)
                    
                    # Fill duplicate member ID
                    update_task_progress(task_id, base_progress + 2, 
                                       step_message=f"📝 Filling duplicate member ID: {dup}")
                    dup_field = wait.until(EC.presence_of_element_located((By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtDupSamagraId")))
                    dup_field.clear()
                    dup_field.send_keys(dup)
                    time.sleep(1)
                    update_task_progress(task_id, base_progress + 3, 
                                       step_message=f"✅ Duplicate member ID entered successfully")
                    
                    # Fill confirm member ID
                    update_task_progress(task_id, base_progress + 4, 
                                       step_message=f"📝 Filling confirm member ID: {conf}")
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtConfirmSamagraId").clear()
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtConfirmSamagraId").send_keys(conf)
                    time.sleep(1)
                    update_task_progress(task_id, base_progress + 5, 
                                       step_message=f"✅ Confirm member ID entered successfully")
                    
                    # Fill original member ID
                    update_task_progress(task_id, base_progress + 6, 
                                       step_message=f"📝 Filling original member ID: {orig}")
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtOriSamagraId").clear()
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtOriSamagraId").send_keys(orig)
                    time.sleep(1)
                    update_task_progress(task_id, base_progress + 7, 
                                       step_message=f"✅ Original member ID entered successfully")
                    
                    # Click show button
                    update_task_progress(task_id, base_progress + 8, 
                                       step_message=f"🔍 Clicking show button to search for member...")
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_BtnShow").click()
                    time.sleep(2)
                    update_task_progress(task_id, base_progress + 10, 
                                       step_message=f"🔍 Searching for member details in database...")
                    
                    # Confirm original member ID
                    update_task_progress(task_id, base_progress + 12, 
                                       step_message=f"📝 Confirming original member ID: {orig}")
                    wait.until(EC.presence_of_element_located((By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtConfirlOriSamagraId"))).send_keys(orig)
                    time.sleep(1)
                    update_task_progress(task_id, base_progress + 14, 
                                       step_message=f"✅ Original member ID confirmed successfully")
                    
                    # Add removal remark
                    update_task_progress(task_id, base_progress + 16, 
                                       step_message=f"📝 Adding removal remark...")
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_txtRemoveRemark").send_keys("Duplicate member removal - automated process")
                    time.sleep(1)
                    update_task_progress(task_id, base_progress + 18, 
                                       step_message=f"✅ Removal remark added successfully")
                    
                    # Check confirmation checkbox
                    update_task_progress(task_id, base_progress + 20, 
                                       step_message=f"☑️ Checking confirmation checkbox...")
                    driver.find_element(By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_chkconfirm").click()
                    update_task_progress(task_id, base_progress + 22, 
                                       step_message=f"✅ Confirmation checkbox checked")
                    
                    # Click delete button
                    update_task_progress(task_id, base_progress + 24, 
                                       step_message=f"🗑️ Clicking delete button to remove member...")
                    wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ctl00_SamagraMain_ContentPlaceHolder1_btnDelete"))).click()
                    time.sleep(2)
                    
                    update_task_progress(task_id, base_progress + 25, 
                                       step_message=f"✅ Member {dup} removed successfully from Family {fam}")
                    
                    success_log.append({
                        "familyid": fam, 
                        "memberid": dup, 
                        "status": "Removed",
                        "timestamp": datetime.now().isoformat(),
                        "original_member": orig
                    })
                    
                except Exception as e:
                    error_msg = str(e)
                    update_task_progress(task_id, base_progress, 
                                       step_message=f"⚠️ Failed to remove member {dup} from Family {fam}: {error_msg}")
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
                progress = 45 + ((idx + 1) / len(tasks)) * 50
                update_task_progress(task_id, progress, 
                                   step_message=f"📊 Progress: {progress:.1f}% ({idx+1}/{len(tasks)} tasks completed)")
                
                time.sleep(1)
            
            # Save logs with timestamp
            update_task_progress(task_id, 95, step_message="💾 Saving automation logs...")
            startRow=start_row+2
            endRow=end_row
            success_filename = f"logs/success_removed_{startRow}_{endRow}.csv"
            fail_filename = f"logs/failed_removal_{startRow}_{endRow}.csv"
            
            # Save detailed logs
            if success_log:
                pd.DataFrame(success_log).to_csv(success_filename, index=False)
                update_task_progress(task_id, 97, step_message=f"✅ Success log saved: {success_filename}")
            
            if fail_log:
                pd.DataFrame(fail_log).to_csv(fail_filename, index=False)
                update_task_progress(task_id, 98, step_message=f"⚠️ Failure log saved: {fail_filename}")
            
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
            
            update_task_progress(task_id, 100, step_message=f"🎉 Automation completed successfully!")
            update_task_progress(task_id, 100, step_message=f"📊 Final Results - Total: {len(tasks)}, Success: {len(success_log)}, Failed: {len(fail_log)}")
            
            return result
            
        finally:
            driver.quit()
            update_task_progress(task_id, 100, step_message="🔒 Browser session closed safely")
            
    except Exception as e:
        update_task_progress(task_id, 0, step_message=f"❌ Automation failed: {e}")
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

def save_cookies_and_run(cookie_name, start_row, end_row, task_id=None):
    """Save cookies from manual login and run automation"""
    global manual_login_driver
    
    if manual_login_driver is None:
        raise Exception("No manual login session found")
    
    try:
        # Save cookies
        update_task_progress(task_id, 10, step_message="💾 Saving authentication cookies...")
        cookie_path = f"cookies/{cookie_name}.pkl"
        with open(cookie_path, "wb") as f:
            pickle.dump(manual_login_driver.get_cookies(), f)
        
        update_task_progress(task_id, 20, step_message=f"✅ Session cookies saved as {cookie_path}")
        
        # Close manual login browser
        manual_login_driver.quit()
        manual_login_driver = None
        update_task_progress(task_id, 25, step_message="🔒 Manual login browser closed")
        
        # Run automation
        return run_automation(cookie_name, start_row, end_row, task_id)
        
    except Exception as e:
        if manual_login_driver:
            manual_login_driver.quit()
            manual_login_driver = None
        raise e