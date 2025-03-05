import pandas as pd
import argparse
from beem import Hive
from beem.account import Account
from datetime import datetime, timedelta
import requests
import json
import math

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

def get_power_down(operations):
    start_date = datetime.utcnow() - timedelta(days=30)
    for op in operations:
        op_time = datetime.strptime(op["timestamp"], "%Y-%m-%dT%H:%M:%S")

        if op_time < start_date:
            break 
        return op['timestamp']  # First occurrence is the latest
    return None

def get_self_votes(username, votes):
    start_date = datetime.utcnow() - timedelta(days=30)
    total_votes = sum(1 for op in votes if datetime.strptime(op["timestamp"], "%Y-%m-%dT%H:%M:%S") >= start_date and op["weight"] > 0)
    self_votes = sum(1 for op in votes if op["voter"] == op["author"] and datetime.strptime(op["timestamp"], "%Y-%m-%dT%H:%M:%S") >= start_date and op["weight"] > 0)

    return round((self_votes / total_votes) * 100, 2) if total_votes > 0 else 0

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

    # Filter users based on command-line arguments
    if 'Verified' in df.columns:
        df = df[df['Verified'] == (args.verified == 'True')]
    if 'Banned' in df.columns:
        df = df[df['Banned'] == (args.banned == 'True')]
    if 'Premium' in df.columns:
        df = df[df['Premium'] == (args.premium == 'True')]

    usernames = df['Account'].dropna().astype(str).tolist()

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
                power_down = get_power_down(account.history_reverse(only_ops=["withdraw_vesting"],stop=datetime.utcnow() - timedelta(days=30),batch_size=500))
                print ("powerdown done")
                self_votes = get_self_votes(username, account.history_reverse(only_ops=["vote"],stop=datetime.utcnow() - timedelta(days=30),batch_size=500))
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
