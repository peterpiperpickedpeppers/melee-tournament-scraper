import pandas as pd

df = pd.read_csv('data/RC Houston 2025/RC Houston 2025 pairings.csv')

player_leading = df['PlayerDeck'].fillna('').str.startswith(' ')
opp_leading = df['OpponentDeck'].fillna('').str.startswith(' ')

print('PlayerDeck with leading space:', player_leading.sum())
print('OpponentDeck with leading space:', opp_leading.sum())

print('\nUnique values with leading spaces:')
if player_leading.any():
    print('PlayerDeck:', df.loc[player_leading, 'PlayerDeck'].unique())
if opp_leading.any():
    print('OpponentDeck:', df.loc[opp_leading, 'OpponentDeck'].unique())

# Also check for trailing spaces
player_trailing = df['PlayerDeck'].fillna('').str.endswith(' ')
opp_trailing = df['OpponentDeck'].fillna('').str.endswith(' ')

print('\nPlayerDeck with trailing space:', player_trailing.sum())
print('OpponentDeck with trailing space:', opp_trailing.sum())

if player_trailing.any():
    print('PlayerDeck trailing:', df.loc[player_trailing, 'PlayerDeck'].unique())
if opp_trailing.any():
    print('OpponentDeck trailing:', df.loc[opp_trailing, 'OpponentDeck'].unique())
