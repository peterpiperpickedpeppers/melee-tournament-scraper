import pandas as pd

# Read Esper Goryo's results
df = pd.read_csv("data/RC Houston 2025/results/Esper Goryo's results.csv")
matches = df[df['OpponentDeck'] == 'Azorius Blink']

print(f'Total matches in Esper Goryo\'s results: {len(matches)}')
print('\nWinningDeck value counts:')
print(matches['WinningDeck'].value_counts())
print('\nPlayerDeck value counts:')
print(matches['PlayerDeck'].value_counts())
print('\nOutcome value counts:')
print(matches['Outcome'].value_counts())

print("\n" + "="*60)

# Read Azorius Blink results
df2 = pd.read_csv("data/RC Houston 2025/results/Azorius Blink results.csv")
matches2 = df2[df2['OpponentDeck'] == "Esper Goryo's"]

print(f'\nTotal matches in Azorius Blink results: {len(matches2)}')
print('\nWinningDeck value counts:')
print(matches2['WinningDeck'].value_counts())
print('\nPlayerDeck value counts:')
print(matches2['PlayerDeck'].value_counts())
print('\nOutcome value counts:')
print(matches2['Outcome'].value_counts())

print("\n" + "="*60)
print("\nLet's check the actual rows:")
print("\nFrom Esper Goryo's results file:")
print(matches[['Player', 'PlayerDeck', 'Opponent', 'OpponentDeck', 'WinningDeck', 'Outcome', 'ResultString']].head(20))
