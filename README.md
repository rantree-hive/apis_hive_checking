# apis_hive_checking


This script processes user data and fetches statistics for Hive users, including reputation, rewards, voting behavior, and more. It pulls data for users from an Excel file and generates a TSV report containing important statistics about each user, such as:

- **HP (Hive Power)** and **Reputation**
- **Rewards (in thousands)**
- **Percentage of HP Delegated**
- **KE (Key Efficiency)**
- **Last Power Down Activity**
- **Self-Vote Percentage (for posts and comments)**

## Requirements

You will need the following Python packages to run the script:

- `pandas`
- `argparse`
- `beem`
- `requests`
- `json`
- `math`
- `openpyxl` (for reading Excel files)

You can install these dependencies via `pip` using the following command:

```bash
pip install pandas argparse beem requests openpyxl


## Usage
Command Line Arguments
To run the script, use the following command:

```bash
python hive_user_stats.py <input_file> [--verified True|False] [--banned True|False] [--premium True|False]

<input_file>: Path to an Excel file that contains a column named Account with Hive usernames.
--verified: Optional filter for users who are marked as verified (True/False).
--banned: Optional filter for users who are marked as banned (True/False).
--premium: Optional filter for users who are marked as premium (True/False).
Example Usage
bash
Copiar
Editar
python hive_user_stats.py users.xlsx --verified True --premium False
This command will process the usernames in users.xlsx, filtering for verified accounts that are not marked as premium.

Input File Format
The Excel file must contain a column named Account with the Hive usernames. Optionally, you can also include the following columns for filtering:

Verified: Whether the user is verified (True/False)
Banned: Whether the user is banned (True/False)
Premium: Whether the user is premium (True/False)
Output
The script generates a TSV file (users_stats.tsv) containing the following columns for each user:

Username: The Hive username
HP: Hive Power
Reputation: User reputation score
Rewards: Total rewards in thousands (posting + curation)
% HP Delegated: Percentage of HP delegated to others
KE (Key Efficiency): Rewards-to-HP ratio
Last Power Down: Timestamp of the last power-down event (if any)
Self Votes (%): Percentage of self-votes in the user's posts/comments in the last 30 days
Example Output
plaintext
Copiar
Editar
Username    HP      Reputation    Rewards    % HP Delegated    KE      Last Power Down    Self Votes (%)
user1       1000    45.23         2500       15.00             2.5     2023-08-10T12:34:56  10.5
user2       500     22.15         1500       30.00             3.0     None                12.3
Functions
get_rep(username)
Fetches the reputation, curation rewards, and vesting shares for a given username.

get_vests_delegated(delegations)
Calculates the total vesting shares delegated to others by the user.

get_power_down(operations)
Checks the last power-down activity for the user in the past 30 days and returns the timestamp of the most recent power-down.

get_self_votes(username, votes)
Calculates the percentage of self-votes made by the user in the past 30 days.

parse_args()
Parses the command-line arguments and handles optional filters for the user data.

main()
The main function that reads the input file, processes user data, and writes the output to a TSV file.
