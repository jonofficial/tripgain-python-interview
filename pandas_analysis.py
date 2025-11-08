import pandas as pd
from typing import Optional, Dict, Any

# Q1 
# loading the dataset into a pandas DataFrame
matches_df = pd.read_csv("matches.csv")

# total number of matches
total_matches = len(matches_df)
print("total matches: ", total_matches)

# column names
column_names = matches_df.columns.tolist()
print("The columns are: ")
print(column_names)

# first 5 rows
first_five_rows = matches_df.head()
print("first 5 rows are: ")
print(first_five_rows)

# describe the dataset
print("describing the dataset: ")
dataset_description = matches_df.describe()
print(dataset_description)

# Q2 
# which player has won the most 'player_of_match' awards in games decided on the final ball? (i.e matches won by just 1 run or 1 wicket)
top_final_player = matches_df['player_of_match'].value_counts().idxmax()
print("Q2 answer: ", top_final_player)

# Q3
# At Wankhede Stadium, is it more common to win by batting first (runs) or by batting second (wickets)?
wankhede_stadium = matches_df[matches_df['venue'] == 'Wankhede Stadium']
batting_first_wins = wankhede_stadium[wankhede_stadium['win_by_runs'] > 0].shape[0]
batting_second_wins = wankhede_stadium[wankhede_stadium['win_by_wickets'] > 0].shape[0]

if batting_first_wins > batting_second_wins:
    print("Q3 answer: At Wankhede Stadium, it is more common to win by batting first")
else:
    print("Q3 answer: At Wankhede Stadium, it is more common to win by batting second")

# Q4
# which team has the highest number of wins where the victory margin was greater than 50 runs?
large_margin_wins = matches_df[matches_df['win_by_runs'] > 50]
team_with_highest_wins = large_margin_wins['team1'].value_counts().idxmax()
print("Q4 answer: ", team_with_highest_wins)

# Q5
# how many times has the team that won the toss also set a target and won the match?
toss_and_match_wins = matches_df[matches_df['toss_winner'] == matches_df['winner']]
count_toss_and_match_wins = toss_and_match_wins.shape[0]
print("Q5 answer: ", count_toss_and_match_wins)

# Q6
#Which of the two umpires (umpire1 or umpire2) has officiated more matches involving the Kolkata Knight Riders?
kkr_matches = matches_df[matches_df['team1'] == 'Kolkata Knight Riders']
umpire1_count = kkr_matches['umpire1'].value_counts().max()
umpire2_count = kkr_matches['umpire2'].value_counts().max()

if umpire1_count > umpire2_count:
    print("Q6 answer: Umpire1")
else:
    print("Q6 answer: Umpire2")
