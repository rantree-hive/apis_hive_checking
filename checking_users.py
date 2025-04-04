import pandas as pd
import argparse
from beem import Hive
from beem.account import Account
from datetime import datetime, timedelta
import requests
import json
import math
import sys


def get_rep(username):
    url = "https://api.openhive.network"
    headers = {"Content-Type": "application/json"}
    data = {
        "jsonrpc": "2.0",
        "method": "condenser_api.get_accounts",
        "params": [[username]],
        "id": 1
    }

    response = requests.post(url, headers=headers, data=json.dumps(data)) 
    result = response.json()

    if 'result' not in result or not result['result']:
        return None, None, None  # User not found

    reputation_raw = int(result['result'][0]['reputation'])
    rewards = result['result'][0]['curation_rewards'] + result['result'][0]['posting_rewards']
    vesting_shares = float(result['result'][0]['vesting_shares'].split(" ")[0])
    
    score = (math.log10(max(1, abs(reputation_raw))) - 9) * 9 + 25 if reputation_raw != 0 else 25
    return round(score, 2), rewards, vesting_shares

def get_vests_delegated(delegations):
    return sum(int(d['vesting_shares']['amount']) for d in delegations)


def get_power_down_api(username):
    url = "https://api.hive.blog"
    stop_time = datetime.utcnow() - timedelta(days=30)
    last_trx_id = -1  # Start from the latest transaction

    while True:
        
        data = {
            "jsonrpc": "2.0",
            "method": "condenser_api.get_account_history",
            "params": [username, last_trx_id, 1000],  # Fetch 1000 transactions per call
            "id": 1
        }
        response = requests.post(url, json=data)
        result = response.json()

        if "result" not in result or not result["result"]:
            
            return None  # No more transactions available

        for trx in reversed(result["result"]):
            trx_id = trx[0]  # Transaction ID
            op = trx[1]["op"]
            timestamp = datetime.strptime(trx[1]["timestamp"], "%Y-%m-%dT%H:%M:%S")
            if op[0] == "withdraw_vesting" or op[0] == "fill_vesting_withdraw":
                #timestamp = datetime.strptime(trx[1]["timestamp"], "%Y-%m-%dT%H:%M:%S")
                if timestamp >= stop_time:
                    return timestamp  # Found a power-down within 30 days

            if timestamp < stop_time:
                
                return None  # Stop if transactions are older than 30 days

        last_trx_id = trx_id - 1  # Move to older transactions

def get_self_votes(username):
    url = "https://api.hive.blog"
    start_date = datetime.utcnow() - timedelta(days=30)
    last_trx_id = -1  # Start from the latest transaction
    total_votes = 0
    self_votes = 0
    reached_30_days = False

    while True:
        data = {
            "jsonrpc": "2.0",
            "method": "condenser_api.get_account_history",
            "params": [username, last_trx_id, 1000],  # Fetch 1000 transactions per call
            "id": 1
        }
        response = requests.post(url, json=data)
        result = response.json()

        if "result" not in result or not result["result"]:
            break  # No more transactions available

        for trx in reversed(result["result"]):
            trx_id = trx[0]  # Transaction ID
            op_time = datetime.strptime(trx[1]["timestamp"], "%Y-%m-%dT%H:%M:%S")

            if op_time < start_date:
                reached_30_days = True  # We've reached transactions older than 30 days
                break

            op = trx[1]["op"]

            if op[0] == "vote":  # Check for vote operations
                op_time = datetime.strptime(trx[1]["timestamp"], "%Y-%m-%dT%H:%M:%S")

                if op_time < start_date:
                    # Stop when reaching 30 days
                    return round((self_votes / total_votes) * 100, 2) if total_votes > 0 else 0.0

                if op[1]["voter"] == username and op[1]["weight"] > 0:  # Check vote weight
                    total_votes += 1
                    if op[1]["voter"] == op[1]["author"]:  # Self-vote
                        self_votes += 1
                

            last_trx_id = trx_id - 1  # Move to older transactions
        if reached_30_days:
                break  # Stop fetching more transactions if we hit 30 days ago

    return round((self_votes / total_votes) * 100, 2) if total_votes > 0 else 0.0

def parse_args():
    parser = argparse.ArgumentParser(description="Process user data and fetch statistics.")
    parser.add_argument('input_file', help="Excel file with user data.")
    parser.add_argument('--verified', type=str, choices=['True', 'False'], default='False', help="Filter users based on 'Verified' column (default: False).")
    parser.add_argument('--banned', type=str, choices=['True', 'False'], default='False', help="Filter users based on 'Banned' column (default: False).")
    parser.add_argument('--premium', type=str, choices=['True', 'False'], default='False', help="Filter users based on 'Premium' column (default: False).")
    return parser.parse_args()

def main():
    args = parse_args()

    # Read Excel file
    df = pd.read_excel(args.input_file)

    # Ensure required column exists
    if 'Account' not in df.columns:
        print("Error: The Excel file must contain an 'Account' column.")
        sys.exit(1)
    
    df.columns = df.columns.str.strip().str.lower()

# Define a mapping for case-insensitive column names
    column_mapping = {
    'verified': next((col for col in df.columns if col.lower() == 'verified'), None),
    'banned': next((col for col in df.columns if col.lower() == 'banned'), None),
    'premium': next((col for col in df.columns if col.lower() == 'premium'), None),
    }
    # Filter users based on command-line arguments
    if 'verified' in df.columns:
        df = df[df['verified'] == (args.verified == 'True')]
    if 'banned' in df.columns:
        df = df[df['banned'] == (args.banned == 'True')]
    if 'premium' in df.columns:
        df = df[df['premium'] == (args.premium == 'True')]
    
    usernames = df['account'].dropna().astype(str).tolist()
    
    hive = Hive(node=["https://api.openhive.network"])

    output_file = 'users_stats.tsv'

    # Write output file
    with open(output_file, 'w') as outfile:
        outfile.write("Username\tHP\tReputation\tRewards\t% HP Delegated\tKE\tLast Power Down\tSelf Votes (%)\n")

        for username in usernames:
            try:
                account = Account(username, blockchain_instance=hive)
                print ("going with ",username)
                rep, rewards, vesting_shares = get_rep(username)
                print ("rep,rewards and vesting_shares done")

                if rep is None:  # Skip if user not found
                    continue

                rewards /= 1000  # Convert to thousands
                hp = round(hive.vests_to_hp(vesting_shares), 2)
                vests_delegated = get_vests_delegated(account.get_vesting_delegations())
                print ("delegations done")
                hp_delegated = hive.vests_to_hp(vests_delegated) / 1_000_000
                power_down = get_power_down_api(username)
                
                print ("powerdown done")
                self_votes = get_self_votes(username)
                print ("Votes done")
                percentage_hp_delegated = round((hp_delegated / hp) * 100, 2) if hp > 0 else 0
                ke = round(rewards / hp, 2) if hp > 0 else 0

                outfile.write(f"{username}\t{hp}\t{rep}\t{rewards}\t{percentage_hp_delegated}\t{ke}\t{power_down}\t{self_votes}\n")
                print(f"Processed: {username} - HP: {hp}, Rep: {rep}, KE: {ke}, Last Power Down: {power_down}, Self Vote %: {self_votes}")
                
            except Exception as e:
                print(f"Error processing {username}: {e}")

    print(f"User stats have been written to {output_file}")

if __name__ == "__main__":
    main()
